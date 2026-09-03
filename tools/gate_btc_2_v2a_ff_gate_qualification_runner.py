#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered FF/Gate Spot V2A source."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.gateio.ws/api/v4"
PAIR = "FF_USDT"
PROVIDER = "GATE"
INTERVAL = "1d"
LIMIT = 1000


def request_bytes(path: str, params: dict[str, str] | None = None, retries: int = 3) -> bytes:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
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


def parse_pair(raw: bytes) -> dict:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("unexpected Gate pair payload type")
    if obj.get("id") != PAIR or obj.get("base") != "FF" or obj.get("quote") != "USDT":
        raise ValueError(f"exact pair identity mismatch: {obj}")
    return obj


def parse_candles(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, list):
        raise ValueError(f"unexpected Gate candle payload: {obj}")
    out: list[dict] = []
    for row in obj:
        if not isinstance(row, list) or len(row) < 7:
            raise ValueError("Gate candle schema mismatch")
        # Gate v4: [timestamp, quote_volume, close, high, low, open, base_volume, ...]
        ts = int(float(row[0]))
        qv = float(row[1]); c = float(row[2]); h = float(row[3]); l = float(row[4]); o = float(row[5]); bv = float(row[6])
        if bv < 0 or qv < 0:
            raise ValueError("negative volume")
        if not (l <= min(o, c) <= max(o, c) <= h):
            raise ValueError("OHLC invariant failed")
        out.append({
            "timestamp_s": ts,
            "day": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
            "open": o, "high": h, "low": l, "close": c,
            "base_volume": bv, "quote_volume": qv,
        })
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--end", required=True)
    p.add_argument("--output", default="artifacts/gate_btc_2/v2a_ff_gate_qualification")
    p.add_argument("--max-pages", type=int, default=10)
    args = p.parse_args()
    out = Path(args.output); out.mkdir(parents=True, exist_ok=True)
    requested_end = date.fromisoformat(args.end)
    end_s = int(datetime.combine(requested_end, datetime.max.time(), tzinfo=timezone.utc).timestamp())

    status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"; error = None
    rows: list[dict] = []; pages: list[dict] = []; boundary_rows_excluded = 0
    duplicate_rows = 0; gaps: list[str] = []; monotonic = False; qa_pass = False
    try:
        raw_pair = request_bytes(f"/spot/currency_pairs/{PAIR}")
        (out / "RAW_PAIR.json").write_bytes(raw_pair)
        pair_sha = hashlib.sha256(raw_pair).hexdigest()
        parse_pair(raw_pair)

        cursor = end_s
        all_rows: list[dict] = []
        seen_oldest: set[int] = set()
        for idx in range(args.max_pages):
            params = {"currency_pair": PAIR, "interval": INTERVAL, "to": str(cursor), "limit": str(LIMIT)}
            raw = request_bytes("/spot/candlesticks", params)
            (out / f"RAW_{idx:03d}.json").write_bytes(raw)
            parsed = parse_candles(raw)
            accepted = [r for r in parsed if date.fromisoformat(r["day"]) <= requested_end]
            excluded = len(parsed) - len(accepted); boundary_rows_excluded += excluded
            pages.append({"page": idx, "request": params, "sha256": hashlib.sha256(raw).hexdigest(), "raw_rows": len(parsed), "accepted_rows": len(accepted), "boundary_rows_excluded": excluded})
            if not parsed:
                break
            all_rows.extend(accepted)
            oldest = min(r["timestamp_s"] for r in parsed)
            if oldest in seen_oldest:
                raise ValueError("pagination repeated oldest timestamp")
            seen_oldest.add(oldest)
            nxt = oldest - 1
            if nxt >= cursor:
                raise ValueError("nondecreasing pagination cursor")
            cursor = nxt
            if len(parsed) < LIMIT:
                break

        dedup = {r["timestamp_s"]: r for r in all_rows}
        rows = sorted(dedup.values(), key=lambda r: r["timestamp_s"])
        duplicate_rows = len(all_rows) - len(rows)
        if not rows:
            raise ValueError("no in-window FF_USDT historical candles returned")
        monotonic = all(rows[i]["timestamp_s"] < rows[i+1]["timestamp_s"] for i in range(len(rows)-1))
        have = {r["day"] for r in rows}; cur = date.fromisoformat(rows[0]["day"]); last = date.fromisoformat(rows[-1]["day"])
        while cur <= last:
            if cur.isoformat() not in have: gaps.append(cur.isoformat())
            cur += timedelta(days=1)
        qa_pass = monotonic and duplicate_rows == 0 and not gaps and date.fromisoformat(rows[-1]["day"]) <= requested_end
    except Exception as exc:
        pair_sha = None; status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"; error = str(exc); rows = []; duplicate_rows = 0; gaps = []; monotonic = False; qa_pass = False

    if not qa_pass and status != "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR": status = "FAIL_CLOSED_FULL_CORPUS_QA"
    summary = {
        "schema_version":"GATE_BTC_2_V2A_FF_GATE_QUALIFICATION_V1","issue":111,"symbol":"FF","coin_id":"falcon-finance-ff",
        "provider":PROVIDER,"market":"SPOT","pair":PAIR,"source_surface":BASE,"interval":INTERVAL,"status":status,
        "research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,
        "no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True,
        "qualification_only":True,"scientific_credit":False,"prospective_credit":False,"dataset_sealed":False,"promotion_allowed":False,
        "admission_scope":"NONE","retroactive_v2a_repair_allowed":False,"requested_end_utc":args.end,"timezone":"UTC",
        "pair_payload_sha256":pair_sha,"pages":pages,"physical_rows_ok":len(rows),"earliest_day":rows[0]["day"] if rows else None,
        "latest_day":rows[-1]["day"] if rows else None,"duplicate_rows":duplicate_rows,"boundary_rows_excluded":boundary_rows_excluded,
        "missing_days_within_returned_interval":gaps,"monotonic":monotonic,"qa_pass":qa_pass,"historical_coverage_sufficiency_asserted":False,
        "source_qualification_outcome":"ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if qa_pass else "FAIL_CLOSED_FULL_CORPUS_QA","error":error,
    }
    (out / "CANDLES.jsonl").write_text("".join(json.dumps(r, sort_keys=True)+"\n" for r in rows), encoding="utf-8")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if qa_pass else 2

if __name__ == "__main__":
    raise SystemExit(main())
