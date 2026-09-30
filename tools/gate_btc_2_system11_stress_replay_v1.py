#!/usr/bin/env python3
"""Deterministic, virtual depth10 stress replay of the approved System11 V1.

Receipt-time sampling limits latency resolution. Missing seconds are rejected,
never carried forward; the fill model does not simulate queue position or profit.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform

from gate_btc_2_system11_collection_status import status as collection_status
from gate_btc_2_system11_lob_replay import validate_snapshot

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_V1_20260929.json"
VENUES = ("BINANCE", "OKX")


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(x):
    return hashlib.sha256(canonical(x).encode()).hexdigest()


def validate_pairs(rows):
    last = {}
    previous_second = None
    for row in rows:
        sec = row.get("pair_second_utc")
        if type(sec) is not int or (previous_second is not None and sec <= previous_second):
            raise ValueError("NON_CAUSAL_OR_DUPLICATE_PAIR")
        if row.get("schema") != "gate_btc.2_0.system11_depth10_pair.v1" or row.get("eligible_pair") is not True:
            raise ValueError("ELIGIBLE_PAIR_SCHEMA_REQUIRED")
        day = datetime.fromtimestamp(sec, timezone.utc).date().isoformat()
        if row.get("observation_date") != day or set(row.get("books", {})) != set(VENUES):
            raise ValueError("PAIR_DATE_OR_VENUES_INVALID")
        for venue in VENUES:
            book = row["books"][venue]
            ms = book.get("receipt_ms")
            if type(ms) is not int or ms // 1000 != sec or ms <= last.get(venue, -1):
                raise ValueError("NON_CAUSAL_RECEIPT_TIMESTAMP")
            validate_snapshot({**book, "venue": venue, "timestamp": datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()})
            if len(book["bids"]) != 10 or len(book["asks"]) != 10:
                raise ValueError("EXACT_DEPTH10_REQUIRED")
            if any(type(x) not in (int, float) for levels in (book["bids"], book["asks"]) for level in levels for x in level):
                raise ValueError("NUMERIC_DEPTH10_REQUIRED")
            last[venue] = ms
        previous_second = sec


def consume(book, side, requested, fee_bps):
    levels = book["asks" if side == "BUY" else "bids"]
    remaining = requested
    fills = []
    for index, (price, quantity) in enumerate(levels):
        take = min(remaining, quantity)
        if take > 0:
            fills.append({"level": index + 1, "price": price, "quantity": take})
            remaining = max(0.0, remaining - take)
        if remaining == 0:
            break
    filled = math.fsum(x["quantity"] for x in fills)
    notional = math.fsum(x["price"] * x["quantity"] for x in fills)
    vwap = notional / filled
    best = levels[0][0]
    mid = (book["bids"][0][0] + book["asks"][0][0]) / 2
    sign = 1 if side == "BUY" else -1
    return {
        "requested_quantity": requested, "filled_quantity": filled,
        "unexecuted_quantity": remaining, "fill_rate": min(1.0, filled / requested),
        "partial_fill": remaining > requested * 1e-12,
        "vwap": vwap, "slippage_best_bps": sign * (vwap / best - 1) * 10000,
        "slippage_mid_bps": sign * (vwap / mid - 1) * 10000,
        "fee_quote": notional * fee_bps / 10000,
        "fee_adjusted_vwap": vwap * (1 + sign * fee_bps / 10000),
        "fill_levels": fills,
    }


def execute_grid(rows, prereg, emit=None):
    grid = prereg["decision_to_execution_contract"]
    percentages = grid["virtual_order_size_grid_percent_of_observed_depth10_side_liquidity"]
    latencies = grid["latency_ms_grid"]
    fees = grid["fee_stress_bps_grid"]
    executions_hash = hashlib.sha256()
    scenarios = []
    monotonicity_violations = 0
    for venue in VENUES:
        times = [r["books"][venue]["receipt_ms"] for r in rows]
        for side in ("BUY", "SELL"):
            for latency in latencies:
                stats = {(pct, fee): {"n": 0, "unavailable": Counter(), "fill_sum": 0.0,
                    "partial": 0, "best_sum": 0.0, "mid_sum": 0.0, "fee_sum": 0.0,
                    "effective_delay_sum": 0.0} for pct in percentages for fee in fees}
                for i, row in enumerate(rows):
                    decision = row["books"][venue]
                    target = times[i] + latency
                    j = bisect_left(times, target, lo=i)
                    reason = None
                    if j == len(rows):
                        reason = "NO_CAUSAL_FUTURE_BOOK"
                    elif rows[j]["pair_second_utc"] > row["pair_second_utc"] + 1:
                        reason = "OBSERVATION_GAP_ABSTAIN"
                    if reason:
                        for value in stats.values():
                            value["unavailable"][reason] += 1
                        continue
                    book = rows[j]["books"][venue]
                    liquidity = math.fsum(x[1] for x in decision["asks" if side == "BUY" else "bids"])
                    previous_vwap = None
                    for pct in percentages:
                        quantity = liquidity * pct / 100
                        base_fill = consume(book, side, quantity, 0)
                        vwap = base_fill["vwap"]
                        if previous_vwap is not None:
                            improvement = previous_vwap - vwap if side == "BUY" else vwap - previous_vwap
                            if improvement > max(abs(vwap), abs(previous_vwap)) * 1e-12:
                                monotonicity_violations += 1
                        previous_vwap = vwap
                        for fee in fees:
                            fill = {**base_fill, "fee_quote": base_fill["filled_quantity"] * vwap * fee / 10000,
                                "fee_adjusted_vwap": vwap * (1 + (1 if side == "BUY" else -1) * fee / 10000)}
                            event = {"venue": venue, "side": side, "size_percent": pct,
                                "latency_ms": latency, "fee_bps": fee,
                                "decision_receipt_ms": times[i], "execution_receipt_ms": times[j], **fill}
                            line = canonical(event) + "\n"
                            executions_hash.update(line.encode())
                            if emit:
                                emit(line)
                            s = stats[pct, fee]
                            s["n"] += 1
                            s["fill_sum"] += fill["fill_rate"]
                            s["partial"] += int(fill["partial_fill"])
                            s["best_sum"] += fill["slippage_best_bps"]
                            s["mid_sum"] += fill["slippage_mid_bps"]
                            s["fee_sum"] += fill["fee_quote"]
                            s["effective_delay_sum"] += times[j] - times[i]
                for (pct, fee), s in stats.items():
                    n = s["n"]
                    scenarios.append({"venue": venue, "side": side, "size_percent": pct,
                        "latency_ms": latency, "fee_bps": fee, "effective_executions": n,
                        "status": "EXECUTED" if n else "UNAVAILABLE", "unavailable_reasons": dict(s["unavailable"]),
                        "fill_rate": s["fill_sum"] / n if n else None,
                        "partial_fills": s["partial"], "full_fills": n - s["partial"],
                        "mean_slippage_best_bps": s["best_sum"] / n if n else None,
                        "mean_slippage_mid_bps": s["mid_sum"] / n if n else None,
                        "total_fee_quote": s["fee_sum"],
                        "mean_effective_delay_ms": s["effective_delay_sum"] / n if n else None})
    return {"scenarios": scenarios, "execution_digest": executions_hash.hexdigest(),
        "size_monotonicity_violations": monotonicity_violations}


def replay(prereg, rows, emit=None):
    authority = json.loads(AUTHORITY.read_text())
    if prereg != authority:
        raise ValueError("FROZEN_V1_CONTRACT_MISMATCH")
    validate_pairs(rows)
    progress = collection_status(prereg, rows)
    first = execute_grid(rows, prereg, emit)
    second = execute_grid(rows, prereg)
    deterministic = first == second
    minimum = prereg["replay"]["minimum_effective_executions_per_primary_scenario"]
    sufficient = all(x["effective_executions"] >= minimum for x in first["scenarios"])
    structural = deterministic and first["size_monotonicity_violations"] == 0
    complete = structural and progress["dataset_gate_ready"] and sufficient and emit is not None
    state = "PASS_FROZEN_LOB_STRESS_REPLAY" if complete else "INCONCLUSIVE_ABSTAIN"
    if not structural:
        state = "FAIL"
    scenarios = first["scenarios"]
    return {
        "schema": "gate_btc.2_0.system11_stress_replay.v1", "status": state,
        "system": 11, "system11_complete": complete, "credit_awarded": complete,
        "collection_progress": progress, "scenario_count": len(scenarios),
        "minimum_execution_gate_ready": sufficient, "deterministic_replay_pass": deterministic,
        "causal_integrity_pass": True, "fills_explainable_by_observed_depth10": True,
        "baseline_execution_result": [x for x in scenarios if x["latency_ms"] == 0 and x["fee_bps"] == 0],
        "stressed_execution_results": scenarios,
        "fill_rate": [{k: x[k] for k in ("venue", "side", "size_percent", "latency_ms", "fee_bps", "fill_rate")} for x in scenarios],
        "vwap_slippage": "mean_slippage_best_bps and mean_slippage_mid_bps per scenario; per-execution VWAP in fill_level_artifacts",
        "size_impact": {"violations": first["size_monotonicity_violations"], "scenario_field": "size_percent"},
        "latency_impact": {"scenario_fields": ["latency_ms", "mean_effective_delay_ms"],
            "resolution": "FIRST_OBSERVED_RECEIPT_AFTER_TARGET; ONE_SNAPSHOT_PER_SECOND; NO_INTERPOLATION"},
        "fee_impact": {"scenario_fields": ["fee_bps", "total_fee_quote"], "currency": "USDT"},
        "partial_fill_distribution": [{k: x[k] for k in ("venue", "side", "size_percent", "latency_ms", "fee_bps", "partial_fills", "full_fills")} for x in scenarios],
        "execution_digest": first["execution_digest"], "dataset_sha256": digest(rows),
        "prereg_sha256": digest(prereg),
        "fill_level_artifacts": {"written": emit is not None, "semantic_digest": first["execution_digest"]},
        "engine_and_version_provenance": {"engine": "QRDS_SYSTEM11_VIRTUAL_DEPTH10_V1", "python": platform.python_version(),
            "engine_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "dependency_source_sha256": {name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                for name in ("gate_btc_2_system11_collection_status.py", "gate_btc_2_system11_lob_replay.py")},
            "git_sha": os.environ.get("GITHUB_SHA"),
            "workflow_run_url": ("https://github.com/" + os.environ["GITHUB_REPOSITORY"] + "/actions/runs/" + os.environ["GITHUB_RUN_ID"])
                if os.environ.get("GITHUB_REPOSITORY") and os.environ.get("GITHUB_RUN_ID") else None},
        "research_only": True, "shadow_only": True, "no_backfill": True, "no_retune": True,
        "orders": 0, "real_capital_brl": 0, "engine_feed": False,
        "automatic_promotion": False, "economic_claim_authorized": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prereg", type=Path, default=AUTHORITY)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    a = ap.parse_args()
    rows = [json.loads(x) for x in a.ledger.read_text().splitlines() if x.strip()]
    a.output_dir.mkdir(parents=True, exist_ok=True)
    fills = a.output_dir / "FILL_LEVELS.jsonl.gz"
    with gzip.open(fills, "wt", encoding="utf-8") as stream:
        result = replay(json.loads(a.prereg.read_text()), rows, stream.write)
    result["fill_level_artifacts"] = {"path": fills.name, "sha256": hashlib.sha256(fills.read_bytes()).hexdigest(),
        "semantic_digest": result["execution_digest"]}
    (a.output_dir / "REPLAY_RESULT.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(canonical({k: result[k] for k in ("status", "scenario_count", "system11_complete", "orders")}))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
