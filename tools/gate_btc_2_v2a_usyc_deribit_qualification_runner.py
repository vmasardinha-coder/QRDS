#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered USYC/Deribit V2A source."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://www.deribit.com/api/v2/public/get_tradingview_chart_data"
PAIR = "USYC_USDC"
PROVIDER = "DERIBIT"
RESOLUTION = "1D"
DEFAULT_START = "2018-01-01"


def request_bytes(params: dict[str, str], retries: int = 3) -> bytes:
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "QRDS-GateBTC2-ResearchOnly/1",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - exercised by live CI
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def parse_payload(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("unexpected Deribit payload type")
    if "error" in obj:
        raise ValueError(f"Deribit error envelope: {obj['error']}")
    result = obj.get("result")
    if not isinstance(result, dict):
        raise ValueError("missing Deribit result object")
    status = result.get("status")
    if status == "no_data":
        return []
    if status != "ok":
        raise ValueError(f"unexpected Deribit result status: {status}")

    keys = ["ticks", "open", "high", "low", "close", "volume", "cost"]
    arrays = {k: result.get(k) for k in keys}
    if any(not isinstance(v, list) for v in arrays.values()):
        raise ValueError("Deribit candle arrays missing or malformed")
    lengths = {len(v) for v in arrays.values()}
    if len(lengths) != 1:
        raise ValueError("Deribit candle arrays have inconsistent lengths")

    out: list[dict] = []
    for i in range(len(arrays["ticks"])):
        ts = int(arrays["ticks"][i])
        o = float(arrays["open"][i])
        h = float(arrays["high"][i])
        l = float(arrays["low"][i])
        c = float(arrays["close"][i])
        bv = float(arrays["volume"][i])
        qv = float(arrays["cost"][i])
        if bv < 0 or qv < 0:
            raise ValueError("negative volume")
        if not (l <= min(o, c) <= max(o, c) <= h):
            raise ValueError("OHLC invariant failed")
        out.append(
            {
                "timestamp_ms": ts,
                "day": datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat(),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "base_volume": bv,
                "quote_volume": qv,
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", required=True)
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument(
        "--output",
        default="artifacts/gate_btc_2/v2a_usyc_deribit_qualification",
    )
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    start_ms = int(datetime.combine(date.fromisoformat(args.start), datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(date.fromisoformat(args.end), datetime.max.time(), tzinfo=timezone.utc).timestamp() * 1000)

    status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"
    error = None
    rows: list[dict] = []
    duplicate_rows = 0
    gaps: list[str] = []
    monotonic = False
    qa_pass = False
    raw_sha256 = None
    params = {
        "instrument_name": PAIR,
        "start_timestamp": str(start_ms),
        "end_timestamp": str(end_ms),
        "resolution": RESOLUTION,
    }

    try:
        raw = request_bytes(params)
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        (out / "RAW_000.json").write_bytes(raw)
        parsed = parse_payload(raw)
        dedup = {r["timestamp_ms"]: r for r in parsed}
        rows = sorted(dedup.values(), key=lambda r: r["timestamp_ms"])
        duplicate_rows = len(parsed) - len(rows)
        if not rows:
            raise ValueError("no USYC_USDC historical candles returned")

        monotonic = all(rows[i]["timestamp_ms"] < rows[i + 1]["timestamp_ms"] for i in range(len(rows) - 1))
        have = {r["day"] for r in rows}
        cur = date.fromisoformat(rows[0]["day"])
        last = date.fromisoformat(rows[-1]["day"])
        while cur <= last:
            if cur.isoformat() not in have:
                gaps.append(cur.isoformat())
            cur += timedelta(days=1)
        qa_pass = monotonic and duplicate_rows == 0 and not gaps
    except Exception as exc:
        status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"
        error = str(exc)
        rows = []
        duplicate_rows = 0
        gaps = []
        monotonic = False
        qa_pass = False

    if not qa_pass and status != "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR":
        status = "FAIL_CLOSED_FULL_CORPUS_QA"

    summary = {
        "schema_version": "GATE_BTC_2_V2A_USYC_DERIBIT_QUALIFICATION_V1",
        "issue": 111,
        "symbol": "USYC",
        "coin_id": "hashnote-usyc",
        "provider": PROVIDER,
        "market": "SPOT",
        "pair": PAIR,
        "source_surface": BASE,
        "resolution": RESOLUTION,
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
        "requested_start_utc": args.start,
        "requested_end_utc": args.end,
        "timezone": "UTC",
        "request": params,
        "raw_sha256": raw_sha256,
        "physical_rows_ok": len(rows),
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "duplicate_rows": duplicate_rows,
        "missing_days_within_returned_interval": gaps,
        "monotonic": monotonic,
        "qa_pass": qa_pass,
        "historical_coverage_sufficiency_asserted": False,
        "source_qualification_outcome": (
            "ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if qa_pass else "FAIL_CLOSED_FULL_CORPUS_QA"
        ),
        "error": error,
    }
    (out / "CANDLES.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8"
    )
    (out / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if qa_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
