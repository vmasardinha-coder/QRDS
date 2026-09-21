#!/usr/bin/env python3
"""Fail-closed physical qualifier for the preregistered REAL / BingX Spot source.

Qualification only. Captures raw public API bytes + SHA-256 and verifies the
exact active spot pair and returned daily-candle corpus. It never admits or
substitutes a source, repairs V2A, backfills history, or grants any credit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

BASE_URL = "https://open-api.bingx.com"
PROVIDER = "BINGX_SPOT"


def request_bytes(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - live CI
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def api_url(path: str, params: dict[str, str]) -> str:
    return BASE_URL + path + "?" + urllib.parse.urlencode(params)


def parse_envelope(raw: bytes) -> object:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("unexpected BingX envelope")
    if int(obj.get("code", -1)) != 0:
        raise ValueError(f"BingX API error: {obj}")
    return obj.get("data")


def parse_identity(raw: bytes, pair: str, base_asset: str, quote_asset: str) -> dict:
    data = parse_envelope(raw)
    if not isinstance(data, dict) or not isinstance(data.get("symbols"), list):
        raise ValueError("unexpected BingX symbols payload")
    hits = [item for item in data["symbols"] if isinstance(item, dict) and item.get("symbol") == pair]
    if len(hits) != 1:
        raise ValueError("exact BingX pair not uniquely present")
    hit = hits[0]
    if str(hit.get("status")) != "1":
        raise ValueError("exact BingX pair is not active")
    parts = pair.split("-")
    if len(parts) != 2 or parts[0] != base_asset or parts[1] != quote_asset:
        raise ValueError("BingX pair identity mismatch")
    return hit


def parse_candles(raw: bytes) -> list[dict]:
    data = parse_envelope(raw)
    if not isinstance(data, list):
        raise ValueError("unexpected BingX kline payload")
    rows: list[dict] = []
    for item in data:
        if not isinstance(item, list) or len(item) < 8:
            raise ValueError("BingX kline schema mismatch")
        ts = int(item[0])
        op = float(item[1]); hi = float(item[2]); lo = float(item[3]); cl = float(item[4])
        bv = float(item[5]); qv = float(item[7])
        if bv < 0 or qv < 0:
            raise ValueError("negative volume")
        if not (lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError("OHLC invariant failed")
        rows.append({
            "timestamp": ts,
            "day": datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat(),
            "open": op,
            "high": hi,
            "low": lo,
            "close": cl,
            "base_volume": bv,
            "quote_volume": qv,
        })
    return rows


def collect(pair: str, base_asset: str, quote_asset: str, cutoff: date, out: Path) -> dict:
    now_ms = int(time.time() * 1000)
    identity_params = {"symbol": pair, "timestamp": str(now_ms)}
    identity_url = api_url("/openApi/spot/v1/common/symbols", identity_params)
    identity_raw = request_bytes(identity_url)
    identity = parse_identity(identity_raw, pair, base_asset, quote_asset)
    (out / "RAW_IDENTITY.json").write_bytes(identity_raw)

    cutoff_ms = int(datetime.combine(cutoff, datetime.max.time(), tzinfo=timezone.utc).timestamp() * 1000)
    kline_params = {
        "symbol": pair,
        "interval": "1d",
        "endTime": str(cutoff_ms),
        "limit": "500",
        "timestamp": str(int(time.time() * 1000)),
    }
    kline_url = api_url("/openApi/market/his/v1/kline", kline_params)
    candle_raw = request_bytes(kline_url)
    parsed = parse_candles(candle_raw)
    (out / "RAW_000.json").write_bytes(candle_raw)

    accepted = [row for row in parsed if date.fromisoformat(row["day"]) <= cutoff]
    boundary_rows_excluded = len(parsed) - len(accepted)
    timestamps = [row["timestamp"] for row in accepted]
    duplicate_rows = len(timestamps) - len(set(timestamps))
    rows = sorted({row["timestamp"]: row for row in accepted}.values(), key=lambda x: x["timestamp"])
    monotonic = all(rows[i]["timestamp"] < rows[i + 1]["timestamp"] for i in range(len(rows) - 1))
    latest_ok = bool(rows) and date.fromisoformat(rows[-1]["day"]) <= cutoff
    qa_pass = bool(rows) and duplicate_rows == 0 and monotonic and latest_ok

    return {
        "identity": identity,
        "identity_sha256": hashlib.sha256(identity_raw).hexdigest(),
        "candle_sha256": hashlib.sha256(candle_raw).hexdigest(),
        "identity_request": identity_params,
        "candle_request": kline_params,
        "rows": rows,
        "raw_rows": len(parsed),
        "duplicate_rows": duplicate_rows,
        "boundary_rows_excluded": boundary_rows_excluded,
        "monotonic": monotonic,
        "qa_pass": qa_pass,
        "source_surface": BASE_URL,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="REAL")
    p.add_argument("--coin-id", default="reallink")
    p.add_argument("--pair", default="REAL-USDT")
    p.add_argument("--base-asset", default="REAL")
    p.add_argument("--quote-asset", default="USDT")
    p.add_argument("--cutoff", default="2026-09-20")
    p.add_argument("--output", required=True)
    args = p.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    result = None
    error = None
    status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"
    try:
        result = collect(args.pair, args.base_asset, args.quote_asset, date.fromisoformat(args.cutoff), out)
        status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION" if result["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA"
    except Exception as exc:
        error = str(exc)

    rows = result["rows"] if result else []
    summary = {
        "schema_version": "GATE_BTC_2_V2A_BINGX_SPOT_QUALIFICATION_V1",
        "symbol": args.symbol,
        "coin_id": args.coin_id,
        "provider": PROVIDER,
        "market": "SPOT",
        "pair": args.pair,
        "base_asset": args.base_asset,
        "quote_asset": args.quote_asset,
        "requested_cutoff_utc": args.cutoff,
        "timezone": "UTC",
        "status": status,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
        "qualification_only": True,
        "scientific_credit": False,
        "prospective_credit": False,
        "dataset_sealed": False,
        "promotion_allowed": False,
        "admission_scope": "NONE",
        "retroactive_v2a_repair_allowed": False,
        "historical_coverage_sufficiency_asserted": False,
        "source_surface": result["source_surface"] if result else None,
        "identity_sha256": result["identity_sha256"] if result else None,
        "candle_sha256": result["candle_sha256"] if result else None,
        "instrument_identity": result["identity"] if result else None,
        "identity_request": result["identity_request"] if result else None,
        "candle_request": result["candle_request"] if result else None,
        "physical_rows_ok": len(rows),
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "raw_rows": result["raw_rows"] if result else 0,
        "duplicate_rows": result["duplicate_rows"] if result else 0,
        "boundary_rows_excluded": result["boundary_rows_excluded"] if result else 0,
        "monotonic": result["monotonic"] if result else False,
        "qa_pass": result["qa_pass"] if result else False,
        "source_qualification_outcome": (
            "ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION"
            if result and result["qa_pass"]
            else "FAIL_CLOSED_FULL_CORPUS_QA"
        ),
        "error": error,
    }
    (out / "CANDLES.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["qa_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
