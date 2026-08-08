#!/usr/bin/env python3
"""Fail-closed transport hardening for public OKX research collection.

This module changes transport behavior only. It does not change the Delta
universe, strategy, factors, prices, return math, evidence gates, prospective
clock, operational approval, orders, or capital use.
"""
from __future__ import annotations

import hashlib
import sys
import time
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - caller already guards public mode
    requests = None

OKX_BASE = "https://www.okx.com"
MAX_ATTEMPTS = 7
CANDLE_PAGE_LIMIT = 300
RETRYABLE_HTTP_STATUS = {408, 425, 429, 500, 502, 503, 504}
RETRYABLE_OKX_CODES = {"50011"}  # documented public-IP rate limit response


def _deterministic_jitter(path: str, params: dict[str, Any], attempt: int) -> float:
    """Small deterministic jitter so tests/replays remain reproducible."""
    token = f"{path}|{sorted(params.items())}|{attempt}".encode("utf-8")
    bucket = int(hashlib.sha256(token).hexdigest()[:8], 16) % 251
    return bucket / 1000.0


def _retry_delay(path: str, params: dict[str, Any], attempt: int, response: Any | None = None) -> float:
    if response is not None:
        retry_after = str(getattr(response, "headers", {}).get("Retry-After", "")).strip()
        try:
            if retry_after:
                return min(15.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    base = min(8.0, 0.75 * (2**attempt))
    return base + _deterministic_jitter(path, params, attempt)


def _request_params(path: str, params: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(params)
    if path == "/api/v5/market/history-candles":
        requested = int(normalized.get("limit", 100))
        normalized["limit"] = min(CANDLE_PAGE_LIMIT, max(requested, CANDLE_PAGE_LIMIT))
    return normalized


def get_json(session: Any, path: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET an OKX public JSON payload with bounded retry and fail-closed semantics."""
    request_params = _request_params(path, params)
    last_error: Exception | None = None

    for attempt in range(MAX_ATTEMPTS):
        response = None
        try:
            response = session.get(OKX_BASE + path, params=request_params, timeout=25)
            status = int(getattr(response, "status_code", 200))
            if status >= 400:
                if status not in RETRYABLE_HTTP_STATUS:
                    response.raise_for_status()
                raise RuntimeError(f"retryable HTTP status={status}")

            payload = response.json()
            code = str(payload.get("code"))
            if code == "0":
                return payload
            if code not in RETRYABLE_OKX_CODES:
                raise ValueError(f"nonretryable OKX code={code} msg={payload.get('msg')}")
            raise RuntimeError(f"retryable OKX code={code} msg={payload.get('msg')}")
        except ValueError:
            # Provider/schema/instrument errors are not transport failures. Do not
            # hide them behind retries or permit fallback approval.
            raise
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= MAX_ATTEMPTS:
                break
            time.sleep(_retry_delay(path, request_params, attempt, response))

    inst_id = request_params.get("instId", "UNKNOWN")
    message = (
        f"OKX transport exhausted attempts={MAX_ATTEMPTS} path={path} "
        f"instId={inst_id} last_error={type(last_error).__name__}: {last_error}"
    )
    print("OKX_TRANSPORT_FAIL " + message, file=sys.stderr, flush=True)
    raise RuntimeError(message) from last_error


def install(delta_module: Any) -> None:
    """Install the transport adapter onto a loaded Delta v1.1-compatible module."""
    delta_module.get_json = get_json
