#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered exact MEXC/Gate spot sources.

Qualification only: preserves raw bytes + SHA-256, exact instrument identity,
UTC cutoff semantics and full returned-corpus QA. It never admits a source,
backfills V2A, grants epoch/scientific credit, feeds an engine, or places orders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

PROVIDERS = {"MEXC", "GATE"}


def request_bytes(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - live CI
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def _url(base: str, path: str, params: dict[str, str] | None = None) -> str:
    out = base + path
    if params:
        out += "?" + urllib.parse.urlencode(params)
    return out


def parse_mexc_identity(raw: bytes, pair: str, base_asset: str, quote_asset: str) -> dict:
    obj = json.loads(raw.decode("utf-8"))
    symbols = obj.get("symbols") if isinstance(obj, dict) else None
    if not isinstance(symbols, list):
        raise ValueError("unexpected MEXC exchangeInfo payload")
    hits = [item for item in symbols if item.get("symbol") == pair]
    if len(hits) != 1:
        raise ValueError("exact MEXC pair not uniquely present")
    hit = hits[0]
    if hit.get("baseAsset") != base_asset or hit.get("quoteAsset") != quote_asset:
        raise ValueError("MEXC instrument identity mismatch")
    return hit


def parse_gate_identity(raw: bytes, pair: str, base_asset: str, quote_asset: str) -> dict:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("unexpected Gate pair payload")
    if obj.get("id") != pair or obj.get("base") != base_asset or obj.get("quote") != quote_asset:
        raise ValueError("Gate instrument identity mismatch")
    return obj


def parse_mexc_candles(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if isinstance(obj, dict):
        raise ValueError(f"unexpected MEXC error/envelope: {obj}")
    if not isinstance(obj, list):
        raise ValueError("unexpected MEXC candle payload")
    rows = []
    for item in obj:
        if not isinstance(item, list) or len(item) < 6:
            raise ValueError("MEXC candle schema mismatch")
        ts = int(item[0]); op, hi, lo, cl, bv = map(float, item[1:6]); qv = float(item[7]) if len(item) > 7 else None
        if bv < 0 or (qv is not None and qv < 0):
            raise ValueError("negative volume")
        if not (lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError("OHLC invariant failed")
        rows.append({"timestamp": ts, "day": datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat(), "open": op, "high": hi, "low": lo, "close": cl, "base_volume": bv, "quote_volume": qv})
    return rows


def parse_gate_candles(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"unexpected Gate candle payload: {obj}")
    rows = []
    for item in obj:
        if not isinstance(item, list) or len(item) < 7:
            raise ValueError("Gate candle schema mismatch")
        ts = int(float(item[0])); qv = float(item[1]); cl = float(item[2]); hi = float(item[3]); lo = float(item[4]); op = float(item[5]); bv = float(item[6])
        if bv < 0 or qv < 0:
            raise ValueError("negative volume")
        if not (lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError("OHLC invariant failed")
        rows.append({"timestamp": ts, "day": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), "open": op, "high": hi, "low": lo, "close": cl, "base_volume": bv, "quote_volume": qv})
    return rows


def collect(provider: str, pair: str, base_asset: str, quote_asset: str, end: date, out: Path, max_pages: int) -> dict:
    if provider == "MEXC":
        base_url = "https://api.mexc.com"
        identity_url = _url(base_url, "/api/v3/exchangeInfo", {"symbol": pair})
        identity_raw = request_bytes(identity_url)
        identity = parse_mexc_identity(identity_raw, pair, base_asset, quote_asset)
        cursor = int(datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).timestamp() * 1000)
    else:
        base_url = "https://api.gateio.ws/api/v4"
        identity_url = _url(base_url, f"/spot/currency_pairs/{pair}")
        identity_raw = request_bytes(identity_url)
        identity = parse_gate_identity(identity_raw, pair, base_asset, quote_asset)
        cursor = int(datetime.combine(end, datetime.max.time(), tzinfo=timezone.utc).timestamp())

    (out / "RAW_IDENTITY.json").write_bytes(identity_raw)
    identity_sha = hashlib.sha256(identity_raw).hexdigest()
    all_rows: list[dict] = []; pages = []; boundary = 0; seen_oldest: set[int] = set()

    for page in range(max_pages):
        if provider == "MEXC":
            params = {"symbol": pair, "interval": "1d", "endTime": str(cursor), "limit": "1000"}
            raw = request_bytes(_url(base_url, "/api/v3/klines", params)); parsed = parse_mexc_candles(raw)
        else:
            params = {"currency_pair": pair, "interval": "1d", "to": str(cursor), "limit": "1000"}
            raw = request_bytes(_url(base_url, "/spot/candlesticks", params)); parsed = parse_gate_candles(raw)
        (out / f"RAW_{page:03d}.json").write_bytes(raw)
        accepted = [row for row in parsed if date.fromisoformat(row["day"]) <= end]
        excluded = len(parsed) - len(accepted); boundary += excluded
        pages.append({"page": page, "request": params, "sha256": hashlib.sha256(raw).hexdigest(), "raw_rows": len(parsed), "accepted_rows": len(accepted), "boundary_rows_excluded": excluded})
        if not parsed:
            break
        all_rows.extend(accepted)
        oldest = min(row["timestamp"] for row in parsed)
        if oldest in seen_oldest:
            raise ValueError("pagination repeated oldest timestamp")
        seen_oldest.add(oldest)
        nxt = oldest - 1
        if nxt >= cursor:
            raise ValueError("nondecreasing pagination cursor")
        cursor = nxt
        if len(parsed) < 1000:
            break

    unique = {row["timestamp"]: row for row in all_rows}
    rows = sorted(unique.values(), key=lambda row: row["timestamp"])
    duplicate_rows = len(all_rows) - len(rows)
    if not rows:
        raise ValueError(f"no in-window {pair} daily candles returned")
    monotonic = all(rows[i]["timestamp"] < rows[i + 1]["timestamp"] for i in range(len(rows) - 1))
    have = {row["day"] for row in rows}; gaps = []; cursor_day = date.fromisoformat(rows[0]["day"]); last = date.fromisoformat(rows[-1]["day"])
    while cursor_day <= last:
        if cursor_day.isoformat() not in have:
            gaps.append(cursor_day.isoformat())
        cursor_day += timedelta(days=1)
    qa_pass = monotonic and duplicate_rows == 0 and not gaps and last <= end
    return {"identity": identity, "identity_sha256": identity_sha, "pages": pages, "rows": rows, "duplicate_rows": duplicate_rows, "boundary_rows_excluded": boundary, "missing_days_within_returned_interval": gaps, "monotonic": monotonic, "qa_pass": qa_pass, "source_surface": base_url}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--coin-id", required=True)
    parser.add_argument("--pair", required=True)
    parser.add_argument("--base-asset", required=True)
    parser.add_argument("--quote-asset", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pages", type=int, default=10)
    args = parser.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"; error = None; result = None
    try:
        result = collect(args.provider, args.pair, args.base_asset, args.quote_asset, date.fromisoformat(args.end), out, args.max_pages)
        if not result["qa_pass"]:
            status = "FAIL_CLOSED_FULL_CORPUS_QA"
    except Exception as exc:
        status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"; error = str(exc)

    rows = result["rows"] if result else []
    summary = {
        "schema_version": "GATE_BTC_2_V2A_EXACT_SPOT_QUALIFICATION_V1", "symbol": args.symbol, "coin_id": args.coin_id,
        "provider": args.provider, "market": "SPOT", "pair": args.pair, "base_asset": args.base_asset, "quote_asset": args.quote_asset,
        "status": status, "research_only": True, "shadow_only": True, "not_approved": True, "engine_feed": False,
        "orders": 0, "real_capital_brl": 0, "no_retune": True, "no_backfill": True, "no_counter_reset": True,
        "no_silent_source_substitution": True, "fail_closed": True, "qualification_only": True, "scientific_credit": False,
        "prospective_credit": False, "dataset_sealed": False, "promotion_allowed": False, "admission_scope": "NONE",
        "retroactive_v2a_repair_allowed": False, "requested_end_utc": args.end, "timezone": "UTC",
        "source_surface": result["source_surface"] if result else None, "identity_sha256": result["identity_sha256"] if result else None,
        "instrument_identity": result["identity"] if result else None, "pages": result["pages"] if result else [],
        "physical_rows_ok": len(rows), "earliest_day": rows[0]["day"] if rows else None, "latest_day": rows[-1]["day"] if rows else None,
        "duplicate_rows": result["duplicate_rows"] if result else 0, "boundary_rows_excluded": result["boundary_rows_excluded"] if result else 0,
        "missing_days_within_returned_interval": result["missing_days_within_returned_interval"] if result else [],
        "monotonic": result["monotonic"] if result else False, "qa_pass": result["qa_pass"] if result else False,
        "historical_coverage_sufficiency_asserted": False,
        "source_qualification_outcome": "ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if result and result["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA",
        "error": error,
    }
    (out / "CANDLES.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["qa_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
