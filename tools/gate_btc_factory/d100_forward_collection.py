#!/usr/bin/env python3
"""Collect physical D100 source evidence; never manufacture scientific credit.

Current CMC membership and same-provider OKX source observations are archived.
Market availability is diagnostic, NOT asset eligibility or an economic ledger.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ACTIVATION_DATE = "2026-09-05"
CMC_URL = "https://pro-api.coinmarketcap.com/public-api/v1/cryptocurrency/map?listing_status=active&limit=100&sort=cmc_rank&aux=status"
OKX_BASE = "https://www.okx.com/api/v5/"
BLOCKERS = [
    "D100_FINAL_N_AND_COMPARISON_PROTOCOL_NOT_DEFINED",
    "D100_LIQUIDITY_THRESHOLD_AND_EXCLUSION_IDENTITIES_NOT_FROZEN",
    "D100_EXECUTABLE_SOURCE_IDENTITY_BINDING_NOT_ADMITTED",
    "D100_DYNAMIC_UNIVERSE_MISSING_DATA_AND_POSITION_EXIT_POLICY_NOT_FROZEN",
]
SAFETY = {
    "research_only": True, "shadow_only": True, "not_approved": True,
    "engine_feed": False, "orders": 0, "real_capital": 0,
    "no_retune": True, "no_backfill": True, "no_counter_reset": True,
    "fail_closed": True, "economics_read": False,
}


def utcnow():
    return datetime.now(timezone.utc)


def stamp(t):
    return t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(s):
    t = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("timezone required")
    return t.astimezone(timezone.utc)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def atomic_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_bytes(packed(obj))
    os.replace(tmp, path)


def request_bytes(url):
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 GATE-BTC-D100-Research-Only/2.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read(8_000_001)
            if not raw or len(raw) > 8_000_000:
                raise ValueError("empty or oversized source response")
            return raw
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(attempt + 1)
    raise RuntimeError(f"source request failed: {type(last).__name__}: {last}")


def top100(payload, available):
    if payload.get("status", {}).get("error_code") != 0:
        raise ValueError("CMC error status")
    source_time = parse_time(payload["status"]["timestamp"])
    if not available - timedelta(hours=1) <= source_time <= available + timedelta(minutes=5):
        raise ValueError("CMC source timestamp stale or future")
    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) != 100:
        raise ValueError("CMC must contain exactly 100 rows")
    ranks, ids = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("malformed CMC row")
        rank = row.get("rank", row.get("cmc_rank"))
        asset_id = row.get("id")
        if type(rank) is not int or type(asset_id) is not int or asset_id <= 0:
            raise ValueError("invalid rank or CMC identity")
        if rank in ranks or asset_id in ids:
            raise ValueError("duplicate rank or CMC identity")
        if row.get("status") != "active" or not row.get("slug") or not row.get("symbol"):
            raise ValueError("missing active identity")
        ranks.add(rank)
        ids.add(asset_id)
    if ranks != set(range(1, 101)):
        raise ValueError("CMC ranks must be exactly 1..100")
    return sorted(rows, key=lambda r: r.get("rank", r.get("cmc_rank")))


def okx_rows(payload):
    if str(payload.get("code")) != "0" or not isinstance(payload.get("data"), list):
        raise ValueError("invalid OKX response")
    return payload["data"]


def collect_sources(fetch=request_bytes, clock=utcnow):
    sources, errors = [], []

    def capture(name, url):
        raw = fetch(url)
        available = clock()  # AFTER the complete response
        payload = json.loads(raw)
        sources.append({"name": name, "url": url, "available_at_utc": stamp(available),
                        "raw_sha256": sha(raw), "raw_utf8": raw.decode("utf-8")})
        return payload, available

    payload, available = capture("cmc_top100", CMC_URL)
    members = top100(payload, available)
    try:
        instruments, _ = capture("okx_swap_instruments", OKX_BASE + "public/instruments?instType=SWAP")
        instruments = okx_rows(instruments)
    except Exception as exc:
        errors.append({"source": "okx_swap_instruments", "error": str(exc)})
        instruments = []
    live = {r.get("instId"): r for r in instruments
            if r.get("state") == "live" and r.get("settleCcy") == "USDT"
            and r.get("ctType") == "linear"}
    symbols = [str(r["symbol"]).upper() for r in members]
    coverage = []
    for member in members:
        symbol = str(member["symbol"]).upper()
        row = {"cmc_id": member["id"], "symbol": symbol,
               "cmc_rank": member.get("rank", member.get("cmc_rank")),
               "economic_eligibility": None, "long_eligible": None, "shortable": None,
               "eligibility_reason": "PENDING_FROZEN_D100_ADMISSION_RULES",
               "source_identity_admitted": False, "market_data_observed": False}
        inst_id = symbol + "-USDT-SWAP"
        if symbols.count(symbol) != 1 or not re.fullmatch(r"[A-Z0-9]{1,20}", symbol):
            row["source_state"] = "AMBIGUOUS_OR_UNSUPPORTED_SYMBOL_NO_SUBSTITUTION"
        elif inst_id not in live:
            row["source_state"] = "NO_EXACT_LIVE_OKX_USDT_SWAP_OBSERVED"
        else:
            row["candidate_instrument_id"] = inst_id
            # Symbol match is source discovery, not proof of asset identity.
            try:
                params = urllib.parse.urlencode({"instId": inst_id, "bar": "1Dutc", "limit": 2})
                candles, candle_time = capture("candles_" + symbol, OKX_BASE + "market/candles?" + params)
                candles = okx_rows(candles)
                closed = [r for r in candles if len(r) >= 9 and str(r[8]) == "1"
                          and int(r[0]) + 86_400_000 <= int(candle_time.timestamp() * 1000)]
                if not closed:
                    raise ValueError("no confirmed closed daily candle")
                candle = max(closed, key=lambda r: int(r[0]))
                day = datetime.fromtimestamp(int(candle[0]) / 1000, timezone.utc).date()
                if day != candle_time.date() - timedelta(days=1):
                    raise ValueError("latest closed candle is stale")
                o, h, low, close, volume = map(float, candle[1:6])
                if not (all(math.isfinite(v) for v in (o, h, low, close, volume))
                        and 0 < low <= min(o, close) <= max(o, close) <= h and volume >= 0):
                    raise ValueError("invalid OHLCV")
                params = urllib.parse.urlencode({"instId": inst_id, "limit": 3})
                funding, funding_time = capture("funding_" + symbol, OKX_BASE + "public/funding-rate-history?" + params)
                funding = okx_rows(funding)
                settled = [r for r in funding if r.get("instId") == inst_id
                           and int(r["fundingTime"]) <= int(funding_time.timestamp() * 1000)]
                if not settled:
                    raise ValueError("no settled funding observation")
                latest = max(settled, key=lambda r: int(r["fundingTime"]))
                if int(latest["fundingTime"]) < int((funding_time - timedelta(days=1)).timestamp() * 1000):
                    raise ValueError("settled funding stale")
                rate = float(latest["fundingRate"])
                if not (-1 < rate < 1):
                    raise ValueError("invalid funding rate")
                row.update(source_state="RAW_MARKET_DATA_OBSERVED_IDENTITY_NOT_ADMITTED",
                           market_data_observed=True, latest_closed_bar_date=day.isoformat(),
                           closed_bar_prospective_credit=0, settled_funding_time=latest["fundingTime"])
            except Exception as exc:
                row["source_state"] = "SOURCE_DATA_FAILURE"
                row["error"] = str(exc)
                errors.append({"source": inst_id, "error": str(exc)})
        coverage.append(row)
    return members, coverage, sources, errors


def verify_history(root):
    previous = None
    records = []
    for path in sorted((root / "snapshots").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        digest = record.pop("record_sha256")
        if sha(packed(record)) != digest or record["previous_record_sha256"] != previous:
            raise ValueError("D100 snapshot hash chain corrupt")
        archive = record["archive"]
        rel = Path(archive["path"])
        if rel.is_absolute() or ".." in rel.parts or rel.parts[0] != "archives":
            raise ValueError("unsafe archive path")
        raw_gz = (root / rel).read_bytes()
        if sha(raw_gz) != archive["sha256"]:
            raise ValueError("D100 source archive missing or corrupt")
        raw = gzip.decompress(raw_gz)
        if sha(raw) != archive["uncompressed_sha256"]:
            raise ValueError("D100 uncompressed archive corrupt")
        bundle = json.loads(raw)
        for source in bundle["sources"]:
            if sha(source["raw_utf8"].encode("utf-8")) != source["raw_sha256"]:
                raise ValueError("D100 raw response corrupt")
        record["record_sha256"] = digest
        records.append(record)
        previous = digest
    return records


def run(output, production_map, fetch=request_bytes, clock=utcnow, run_id="manual"):
    started = clock()
    root = output.parent
    row = next((x for x in production_map.get("tracks", []) if x.get("track") == "D100"), {})
    if row.get("collect") is not True or row.get("evolve") is not False or row.get("state") not in {"DATA_FEED_ONLY", "COLLECT_ONLY_FROZEN"}:
        raise ValueError("D100 authority must be collect=true/evolve=false with data-only or approved frozen-shadow authority")
    prior = json.loads(output.read_text(encoding="utf-8")) if output.exists() else {}
    if prior.get("scientific_observations_credited", 0) != 0 or prior.get("economics_enabled", False):
        raise ValueError("unexpected scientific authority: refuse counter reset")
    records = verify_history(root)
    if prior.get("physical_snapshot_count", 0) > len(records):
        raise ValueError("D100 recorded evidence has disappeared")
    if records and parse_time(records[-1]["captured_at_utc"]) > started:
        raise ValueError("D100 time regression")
    current_good = next((r for r in reversed(records) if r["capture_date"] == started.date().isoformat()
                         and not r["source_failures"]), None)
    base = {
        "schema": "qrds.d100.forward_collection.v2", "track": "D100",
        "collection_enabled": True, "collection_mode": "PHYSICAL_FORWARD_SOURCE_EVIDENCE_ONLY",
        "activation_date": ACTIVATION_DATE, "last_heartbeat_utc": stamp(started),
        "last_attempt_at_utc": stamp(started), "historical_recovery_attempted": False,
        "historical_period_before_activation": "EXPLICIT_GAP_NOT_RECOVERED",
        "backfill_performed": False, "historical_observations_credited": 0,
        "scientific_observations_credited": 0, "scientific_target": None,
        "remaining_scientific_observations": None, "economics_enabled": False,
        "economic_status": "BLOCKED_UNRESOLVED_SCIENTIFIC_SPECIFICATION",
        "scientific_blockers": BLOCKERS, "safety": SAFETY,
        "next_action": "RESOLVE_D100_SCIENTIFIC_CONTRACT_WHILE_COLLECTING_PHYSICAL_SOURCE_EVIDENCE",
        "workflow_run_id": str(run_id),
    }
    approved = row.get("state") == "COLLECT_ONLY_FROZEN"
    terminal = False
    economic_status_path = root / "economic/STATUS.json"
    if economic_status_path.exists():
        economic_status = json.loads(economic_status_path.read_text(encoding="utf-8"))
        if str(economic_status.get("status", "")).startswith("CLOSED_"):
            if __package__ in (None, ""):
                sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
            from tools.gate_btc_factory.d100_economics import verify
            _, economic_rows = verify(root / "economic")
            if len(economic_rows) != 80 or not (root / "economic/FINAL_DECISION.json").exists():
                raise ValueError("unverified terminal D100 state")
            terminal = True
    if approved:
        base.update(economic_status="SEE_SEPARATE_APPROVED_ECONOMIC_AUTHORITY", scientific_blockers=[],
                    next_action="READ_ECONOMIC_STATUS_FOR_APPROVED_N80_PROGRESS")
    failure = None
    if terminal:
        result = "TERMINAL_N80_NO_MORE_SOURCE_REQUESTS"
        latest = records[-1] if records else None
    elif current_good:
        result = "IDEMPOTENT_ALREADY_CAPTURED_TODAY"
        latest = current_good
    else:
        try:
            members, coverage, sources, errors = collect_sources(fetch, clock)
            finished = clock()
            if finished.date() != started.date():
                raise ValueError("capture crossed UTC day; retry with new contemporaneous membership")
            captured = stamp(finished)
            bundle = {"members": members, "coverage": coverage, "sources": sources}
            raw = packed(bundle)
            zipped = gzip.compress(raw, mtime=0)
            snapshot_id = finished.strftime("%Y%m%dT%H%M%S%fZ") + "_" + sha(raw)[:12]
            archive_rel = "archives/" + snapshot_id + ".json.gz"
            archive_path = root / archive_rel
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with archive_path.open("xb") as f:
                f.write(zipped)
            latest = {
                "schema": "qrds.d100.physical_capture.v1", "snapshot_id": snapshot_id,
                "capture_date": finished.date().isoformat(), "captured_at_utc": captured,
                "universe_available_at_utc": sources[0]["available_at_utc"],
                "sequence": len(records) + 1,
                "previous_record_sha256": records[-1]["record_sha256"] if records else None,
                "raw_universe_count": len(members), "market_data_observed_count": sum(r["market_data_observed"] for r in coverage),
                "economic_eligible_count": None, "source_failures": errors,
                "scientific_observations_credited": 0, "economic_credit": 0,
                "source_code_sha": os.environ.get("GITHUB_SHA", "local"), "workflow_run_id": str(run_id),
                "archive": {"path": archive_rel, "sha256": sha(zipped), "uncompressed_sha256": sha(raw)},
                "safety": SAFETY,
            }
            latest["record_sha256"] = sha(packed(latest))
            dest = root / "snapshots" / (snapshot_id + ".json")
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open("xb") as f:
                f.write(packed(latest))
            records.append(latest)
            result = "CAPTURED" if not errors else "CAPTURED_WITH_SOURCE_FAILURES"
            failure = "; ".join(e["error"] for e in errors) if errors else None
        except Exception as exc:
            latest = records[-1] if records else None
            failure = f"{type(exc).__name__}: {exc}"
            result = "FAILED_NO_VALID_NEW_CAPTURE"
    base.update(
        status="CLOSED_PHYSICAL_FEED_N80" if terminal else ("PHYSICAL_DATA_FEED_SOURCE_FAILURE" if failure else "ACTIVE_PHYSICAL_DATA_FEED"),
        collection_enabled=not terminal,
        last_attempt_result=result, last_error=failure,
        physical_snapshot_count=len(records),
        distinct_capture_days=len({r["capture_date"] for r in records}),
        successful_capture_days=len({r["capture_date"] for r in records if not r["source_failures"]}),
        first_physical_capture_at_utc=records[0]["captured_at_utc"] if records else None,
        latest_physical_capture_at_utc=latest["captured_at_utc"] if latest else None,
        latest_snapshot_id=latest["snapshot_id"] if latest else None,
        latest_snapshot_sha256=latest["record_sha256"] if latest else None,
        latest_raw_universe_count=latest["raw_universe_count"] if latest else 0,
        latest_market_data_observed_count=latest["market_data_observed_count"] if latest else 0,
        latest_source_failure_count=len(latest["source_failures"]) if latest else None,
        next_expected_capture_date=None if terminal else ((started.date() + timedelta(days=1)).isoformat() if not failure else started.date().isoformat()),
    )
    atomic_json(output, base)
    text = ["# D100 — operational evidence", "", f"Status: {base['status']}",
            f"Last attempt: {result}", f"Physical captures: {len(records)}; distinct days: {base['distinct_capture_days']}",
            f"Latest physical capture: {base['latest_physical_capture_at_utc']}",
            f"Raw universe: {base['latest_raw_universe_count']}; market data observed: {base['latest_market_data_observed_count']}",
            "Physical feed scientific credit: 0. Approved economic authority: economic/STATUS.json." if approved else "Scientific observations: 0 / NOT_DEFINED; economics: BLOCKED.",
            "Physical source captures do not count toward a scientific gate. Symbol matching does not admit an execution source.",
            "", "Separate approved economic protocol is authoritative." if approved else "Required scientific definitions:"] + (["- " + x for x in BLOCKERS] if not approved else [])
    if failure:
        text += ["", "Source failure: " + failure]
    (root / "D100_STATUS.md").write_text("\n".join(text) + "\n", encoding="utf-8")
    print(json.dumps(base, sort_keys=True))
    return 2 if failure else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default="tools/gate_btc_factory/PRODUCTION_LINE_MAP.v1.json")
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    return run(args.output, json.loads(Path(args.map).read_text(encoding="utf-8")),
               run_id=os.environ.get("GITHUB_RUN_ID", "manual"))


if __name__ == "__main__":
    raise SystemExit(main())
