#!/usr/bin/env python3
"""Capture and QA preregistered V2A source-redundancy batch 1.

Qualification-only. Historical captures produced here receive no scientific,
prospective, dataset-seal, engine, order, or capital credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
SOURCES = {
    "KCS": {"provider": "KuCoin", "pair": "KCS-USDT", "base": "https://api.kucoin.com/api/v1/market/candles", "unit": "s", "chunk_days": 1200},
    "BGB": {"provider": "Bitget", "pair": "BGBUSDT", "base": "https://api.bitget.com/api/v3/market/history-candles", "unit": "ms", "chunk_days": 89},
    "GT": {"provider": "Gate", "pair": "GT_USDT", "base": "https://api.gateio.ws/api/v4/spot/candlesticks", "unit": "s", "chunk_days": 900},
}


def ts(date_text: str) -> int:
    return int(datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def request_bytes(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as exc:  # fail closed after bounded retry
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def page_url(symbol: str, start: int, end: int) -> str:
    s = SOURCES[symbol]
    if symbol == "KCS":
        q = {"symbol": s["pair"], "type": "1day", "startAt": start, "endAt": end}
    elif symbol == "BGB":
        q = {"category": "SPOT", "symbol": s["pair"], "interval": "1D", "startTime": start * 1000, "endTime": end * 1000, "limit": 100, "type": "market"}
    else:
        q = {"currency_pair": s["pair"], "interval": "1d", "from": start, "to": end}
    return s["base"] + "?" + urllib.parse.urlencode(q)


def parse_rows(symbol: str, raw: bytes) -> list[dict]:
    payload = json.loads(raw)
    if symbol == "KCS":
        if payload.get("code") != "200000":
            raise ValueError(f"KuCoin non-success payload: {payload.get('code')}")
        data = payload.get("data") or []
        return [{"t": int(x[0]), "o": float(x[1]), "c": float(x[2]), "h": float(x[3]), "l": float(x[4]), "v": float(x[5])} for x in data]
    if symbol == "BGB":
        if payload.get("code") != "00000":
            raise ValueError(f"Bitget non-success payload: {payload.get('code')}")
        data = payload.get("data") or []
        return [{"t": int(x[0]) // 1000, "o": float(x[1]), "h": float(x[2]), "l": float(x[3]), "c": float(x[4]), "v": float(x[5])} for x in data]
    if not isinstance(payload, list):
        raise ValueError("Gate non-list payload")
    return [{"t": int(x[0]), "v": float(x[1]), "c": float(x[2]), "h": float(x[3]), "l": float(x[4]), "o": float(x[5])} for x in payload]


def qa(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda r: r["t"])
    times = [r["t"] for r in ordered]
    duplicates = len(times) - len(set(times))
    internal_missing_days = sum(max(0, round((b - a) / DAY) - 1) for a, b in zip(times, times[1:]))
    bad_ohlc = sum(not (r["l"] <= min(r["o"], r["c"]) <= max(r["o"], r["c"]) <= r["h"]) for r in ordered)
    bad_volume = sum(r["v"] < 0 for r in ordered)
    monotonic = all(b > a for a, b in zip(times, times[1:]))
    return {
        "rows": len(ordered),
        "earliest_utc": datetime.fromtimestamp(times[0], timezone.utc).date().isoformat() if times else None,
        "latest_utc": datetime.fromtimestamp(times[-1], timezone.utc).date().isoformat() if times else None,
        "duplicates": duplicates,
        "internal_missing_days": internal_missing_days,
        "bad_ohlc": bad_ohlc,
        "bad_volume": bad_volume,
        "strict_monotonic_after_sort": monotonic,
        "qa_pass": bool(ordered) and duplicates == 0 and internal_missing_days == 0 and bad_ohlc == 0 and bad_volume == 0 and monotonic,
    }


def capture(symbol: str, start: int, end: int, out: Path) -> dict:
    src = SOURCES[symbol]
    symbol_dir = out / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    rows, pages = [], []
    cursor = start
    chunk = src["chunk_days"] * DAY
    index = 0
    while cursor <= end:
        stop = min(end, cursor + chunk - DAY)
        url = page_url(symbol, cursor, stop)
        raw = request_bytes(url)
        digest = hashlib.sha256(raw).hexdigest()
        raw_path = symbol_dir / f"raw_{index:04d}.json"
        raw_path.write_bytes(raw)
        parsed = parse_rows(symbol, raw)
        rows.extend(parsed)
        pages.append({"request_url": url, "raw_file": str(raw_path.relative_to(out)), "sha256": digest, "parsed_rows": len(parsed)})
        cursor = stop + DAY
        index += 1
    result = {
        "symbol": symbol,
        "provider": src["provider"],
        "pair": src["pair"],
        "qualification_only": True,
        "scientific_credit": False,
        "prospective_credit": False,
        "dataset_sealed": False,
        "promotion_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill_credit": True,
        "no_silent_source_substitution": True,
        "requested_discovery_window": {"start": datetime.fromtimestamp(start, timezone.utc).date().isoformat(), "end": datetime.fromtimestamp(end, timezone.utc).date().isoformat()},
        "pages": pages,
        "qa": qa(rows),
    }
    (symbol_dir / "qualification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2017-01-01", help="discovery horizon only; not a scientific cutoff")
    p.add_argument("--end", required=True, help="inclusive UTC date")
    p.add_argument("--output", default="artifacts/gate_btc_2/v2a_source_qualification_batch1")
    args = p.parse_args()
    start, end = ts(args.start), ts(args.end)
    if end < start:
        raise SystemExit("end before start")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for symbol in SOURCES:
        try:
            results.append(capture(symbol, start, end, out))
        except Exception as exc:
            results.append({"symbol": symbol, "provider": SOURCES[symbol]["provider"], "pair": SOURCES[symbol]["pair"], "qualification_only": True, "scientific_credit": False, "status": "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR", "error": str(exc)})
    summary = {
        "schema_version": "GATE_BTC_2_V2A_SOURCE_QUALIFICATION_BATCH1_CAPTURE_V1",
        "status": "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION",
        "issue": 111,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill_credit": True,
        "no_silent_source_substitution": True,
        "dataset_sealed": False,
        "results": results,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
