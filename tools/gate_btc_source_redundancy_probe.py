#!/usr/bin/env python3
"""Public-source redundancy probes that never feed the frozen GATE BTC engine."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

BASE = "https://data.binance.vision"
DEFAULT_SYMBOLS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def fetch_bytes(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-research-source-probe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise urllib.error.HTTPError(url, response.status, "non-200", response.headers, None)
        return response.read()


def parse_checksum(raw: bytes) -> str:
    text = raw.decode("utf-8-sig", errors="strict").strip()
    if not text:
        raise ValueError("empty checksum file")
    token = text.split()[0].strip()
    if not HEX64.fullmatch(token):
        raise ValueError("invalid SHA-256 checksum format")
    return token.lower()


def timestamp_day(value: str) -> str:
    number = int(float(value))
    if number > 10**17:
        seconds = number / 1_000_000_000
    elif number > 10**14:
        seconds = number / 1_000_000
    else:
        seconds = number / 1_000
    return datetime.fromtimestamp(seconds, tz=timezone.utc).date().isoformat()


def validate_daily_1d_zip(raw_zip: bytes, expected_day: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member: {bad}")
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {len(members)}")
        raw_csv = archive.read(members[0])
    rows = list(csv.reader(io.StringIO(raw_csv.decode("utf-8-sig", errors="strict"))))
    if not rows:
        raise ValueError("empty kline CSV")
    if rows and (not rows[0] or not rows[0][0].strip().replace(".", "", 1).isdigit()):
        rows = rows[1:]
    if not rows:
        raise ValueError("kline CSV has header but no data rows")
    if any(len(row) != 12 for row in rows):
        raise ValueError("kline CSV does not have the expected 12 columns")
    days = sorted({timestamp_day(row[0]) for row in rows})
    if days != [expected_day]:
        raise ValueError(f"archive UTC day mismatch: {days} != [{expected_day}]")
    return {
        "member": members[0],
        "row_count": len(rows),
        "utc_days": days,
        "first_open_time": rows[0][0],
        "last_close": rows[-1][4],
        "csv_sha256": sha256_bytes(raw_csv),
    }


def probe_symbol(symbol: str, day: str, fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    filename = f"{symbol}-1d-{day}.zip"
    path = f"/data/futures/um/daily/klines/{symbol}/1d/{filename}"
    url = BASE + path
    checksum_url = url + ".CHECKSUM"
    result = {
        "symbol": symbol,
        "requested_day": day,
        "archive_path": path,
        "checksum_path": path + ".CHECKSUM",
        "status": "RUNNING",
    }
    try:
        checksum_raw = fetcher(checksum_url)
        archive_raw = fetcher(url)
        expected = parse_checksum(checksum_raw)
        actual = sha256_bytes(archive_raw)
        if actual != expected:
            raise ValueError(f"checksum mismatch: {actual} != {expected}")
        content = validate_daily_1d_zip(archive_raw, day)
        result.update({
            "status": "PASS",
            "archive_sha256": actual,
            "checksum_sha256_expected": expected,
            "archive_size_bytes": len(archive_raw),
            **content,
        })
    except urllib.error.HTTPError as exc:
        result.update({
            "status": "NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR",
            "http_status": exc.code,
            "error": str(exc)[:300],
        })
    except (urllib.error.URLError, TimeoutError) as exc:
        result.update({"status": "NETWORK_ERROR", "error": str(exc)[:300]})
    except (ValueError, zipfile.BadZipFile, UnicodeError, OSError) as exc:
        result.update({"status": "FAIL_INTEGRITY", "error": str(exc)[:500]})
    return result


def run_probe(day: str, symbols: list[str], fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    date.fromisoformat(day)
    normalized = []
    for symbol in symbols:
        s = symbol.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{4,30}", s):
            raise ValueError(f"invalid symbol: {symbol}")
        if s not in normalized:
            normalized.append(s)
    if not normalized:
        raise ValueError("at least one symbol is required")
    results = [probe_symbol(symbol, day, fetcher) for symbol in normalized]
    counts = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    if counts.get("FAIL_INTEGRITY", 0):
        status = "FAIL_INTEGRITY"
    elif counts.get("PASS", 0) == len(results):
        status = "PASS"
    elif counts.get("PASS", 0):
        status = "PASS_PARTIAL"
    else:
        status = "WARN_UNAVAILABLE"
    return {
        "schema": "gate_btc.public_source_redundancy_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": "BINANCE_PUBLIC_DATA_USDM_DAILY_KLINES",
        "requested_day": day,
        "interval": "1d",
        "symbols": normalized,
        "status_counts": counts,
        "results": results,
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", required=True)
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = run_probe(args.day, args.symbols.split(","))
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
