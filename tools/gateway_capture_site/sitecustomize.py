"""Capture/replay public HTTP responses for canonical Gateway validation.

Loaded automatically through PYTHONPATH only inside the dedicated research-only
validation subprocess. It records no request headers or credentials and fails
closed on any replay request that was not captured.
"""
from __future__ import annotations

import atexit
import base64
import hashlib
import json
import os
import threading
from collections import defaultdict, deque
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MODE = os.environ.get("GATE_BTC_HTTP_MODE", "off").strip().lower()
CASSETTE = Path(os.environ.get("GATE_BTC_HTTP_CASSETTE", "gateway_http_cassette.jsonl"))
STATUS = Path(os.environ.get("GATE_BTC_HTTP_STATUS", "gateway_http_status.json"))
VOLATILE_QUERY_KEYS = {
    "timestamp", "starttime", "endtime", "start_time", "end_time",
    "since", "until", "from", "to", "begin", "end", "recvwindow",
}
_LOCK = threading.RLock()
_CAPTURE_COUNT = 0
_REPLAY_TOTAL = 0
_REPLAY_CONSUMED = 0
_REPLAY_UNMATCHED: list[dict] = []
_REPLAY_QUEUES: dict[str, deque] = defaultdict(deque)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _prepared_signature(method: str, url: str, kwargs: dict) -> tuple[str, dict]:
    import requests

    request = requests.Request(
        method=str(method).upper(),
        url=str(url),
        params=kwargs.get("params"),
        data=kwargs.get("data"),
        json=kwargs.get("json"),
    ).prepare()
    parsed = urlsplit(request.url)
    normalized_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        normalized_pairs.append(
            (key, "<VOLATILE>" if key.lower() in VOLATILE_QUERY_KEYS else value)
        )
    normalized_pairs.sort()
    normalized_url = urlunsplit(
        (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, urlencode(normalized_pairs), "")
    )
    body = request.body
    if body is None:
        body_bytes = b""
    elif isinstance(body, bytes):
        body_bytes = body
    else:
        body_bytes = str(body).encode("utf-8", errors="replace")
    descriptor = {
        "method": str(method).upper(),
        "url": normalized_url,
        "body_sha256": hashlib.sha256(body_bytes).hexdigest(),
    }
    key = hashlib.sha256(
        json.dumps(descriptor, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return key, descriptor


def _append_capture(record: dict) -> None:
    global _CAPTURE_COUNT
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    with _LOCK:
        CASSETTE.parent.mkdir(parents=True, exist_ok=True)
        with CASSETTE.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())
        _CAPTURE_COUNT += 1


def _load_replay() -> None:
    global _REPLAY_TOTAL
    if not CASSETTE.is_file():
        raise RuntimeError(f"HTTP cassette not found: {CASSETTE}")
    for line_number, line in enumerate(CASSETTE.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        record = json.loads(line)
        record["cassette_line"] = line_number
        _REPLAY_QUEUES[record["signature"]].append(record)
        _REPLAY_TOTAL += 1
    if not _REPLAY_TOTAL:
        raise RuntimeError("HTTP cassette is empty")


def _write_status() -> None:
    remaining = sum(len(queue) for queue in _REPLAY_QUEUES.values()) if MODE == "replay" else 0
    payload = {
        "schema": "gate-btc-gateway-http-cassette-v1",
        "mode": MODE,
        "capture_count": _CAPTURE_COUNT,
        "replay_total": _REPLAY_TOTAL,
        "replay_consumed": _REPLAY_CONSUMED,
        "replay_remaining": remaining,
        "unmatched_requests": _REPLAY_UNMATCHED,
        "status": (
            "PASS"
            if (MODE == "capture" and _CAPTURE_COUNT > 0)
            or (
                MODE == "replay"
                and _REPLAY_TOTAL > 0
                and _REPLAY_CONSUMED == _REPLAY_TOTAL
                and remaining == 0
                and not _REPLAY_UNMATCHED
            )
            else "FAIL"
        ),
        "research_only": True,
        "orders": 0,
        "real_capital": 0,
        "operational_status": "NOT_APPROVED",
    }
    try:
        _atomic_json(STATUS, payload)
    except Exception:
        pass


def _install() -> None:
    global _REPLAY_CONSUMED
    if MODE not in {"capture", "replay"}:
        return

    import requests

    if MODE == "capture":
        CASSETTE.parent.mkdir(parents=True, exist_ok=True)
        CASSETTE.write_text("", encoding="utf-8")
    else:
        _load_replay()

    original_request = requests.sessions.Session.request

    def wrapped_request(session, method, url, **kwargs):
        global _REPLAY_CONSUMED
        signature, descriptor = _prepared_signature(method, url, kwargs)
        if MODE == "capture":
            try:
                response = original_request(session, method, url, **kwargs)
            except Exception as exc:
                _append_capture(
                    {
                        "signature": signature,
                        "request": descriptor,
                        "exception": {
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    }
                )
                raise
            _append_capture(
                {
                    "signature": signature,
                    "request": descriptor,
                    "response": {
                        "status_code": int(response.status_code),
                        "reason": str(response.reason or ""),
                        "url": str(response.url or url),
                        "encoding": response.encoding,
                        "headers": {
                            key: value
                            for key, value in response.headers.items()
                            if key.lower() in {"content-type", "date", "retry-after"}
                        },
                        "body_base64": base64.b64encode(response.content).decode("ascii"),
                        "body_sha256": hashlib.sha256(response.content).hexdigest(),
                    },
                }
            )
            return response

        with _LOCK:
            queue = _REPLAY_QUEUES.get(signature)
            if not queue:
                finding = {"signature": signature, "request": descriptor}
                _REPLAY_UNMATCHED.append(finding)
                raise RuntimeError(f"UNCAPTURED_PUBLIC_HTTP_REQUEST: {json.dumps(finding, sort_keys=True)}")
            record = queue.popleft()
            _REPLAY_CONSUMED += 1

        if "exception" in record:
            raise requests.exceptions.RequestException(record["exception"].get("message", "captured request failure"))

        stored = record["response"]
        body = base64.b64decode(stored["body_base64"], validate=True)
        if hashlib.sha256(body).hexdigest() != stored["body_sha256"]:
            raise RuntimeError("CAPTURED_HTTP_BODY_HASH_MISMATCH")
        response = requests.Response()
        response.status_code = int(stored["status_code"])
        response.reason = stored.get("reason") or ""
        response.url = stored.get("url") or str(url)
        response.encoding = stored.get("encoding")
        response.headers.update(stored.get("headers") or {})
        response._content = body
        response.request = requests.Request(method=str(method).upper(), url=str(url)).prepare()
        return response

    requests.sessions.Session.request = wrapped_request
    atexit.register(_write_status)


_install()
