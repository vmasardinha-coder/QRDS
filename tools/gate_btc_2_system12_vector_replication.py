#!/usr/bin/env python3
"""Implementation-independent NumPy depth-consumption replication.

No System11 engine imports. This is implementation parity, not external or
organizational independence, profitability, survivor adjudication or promotion.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "artifacts/gate_btc_2/SYSTEM12_IMPLEMENTATION_REPLICATION_V1_20261010.json"
VENUES = ("BINANCE", "OKX")
FILL_FIELDS = ("requested_quantity", "filled_quantity", "unexecuted_quantity",
               "fill_rate", "vwap", "slippage_best_bps", "slippage_mid_bps",
               "fee_quote", "fee_adjusted_vwap")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode()).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(rows, prereg):
    if not rows:
        raise ValueError("EMPTY_DATASET")
    seconds = []
    dates = []
    for row in rows:
        second = row.get("pair_second_utc")
        if type(second) is not int or row.get("eligible_pair") is not True:
            raise ValueError("INVALID_CAUSAL_PAIR")
        if row.get("schema") != "gate_btc.2_0.system11_depth10_pair.v1":
            raise ValueError("INVALID_PAIR_SCHEMA")
        day = datetime.fromtimestamp(second, timezone.utc).date().isoformat()
        if row.get("observation_date") != day or set(row.get("books", {})) != set(VENUES):
            raise ValueError("INVALID_DATE_OR_VENUES")
        seconds.append(second)
        dates.append(day)
        for venue in VENUES:
            book = row["books"][venue]
            if book.get("symbol") != "BTC-USDT" or type(book.get("receipt_ms")) is not int:
                raise ValueError("INVALID_BOOK_IDENTITY")
            if book["receipt_ms"] // 1000 != second:
                raise ValueError("INVALID_RECEIPT_SECOND")
            for side in ("bids", "asks"):
                levels = book.get(side)
                if not isinstance(levels, list) or len(levels) != 10:
                    raise ValueError("EXACT_DEPTH10_REQUIRED")
                if any(not isinstance(level, list) or len(level) != 2 or
                       any(type(x) not in (int, float) for x in level) for level in levels):
                    raise ValueError("NUMERIC_LEVEL_REQUIRED")
    seconds = np.asarray(seconds, dtype=np.int64)
    if np.any(np.diff(seconds) <= 0):
        raise ValueError("NON_CAUSAL_OR_DUPLICATE_PAIR")
    books = {}
    for venue in VENUES:
        times = np.asarray([r["books"][venue]["receipt_ms"] for r in rows], dtype=np.int64)
        bid = np.asarray([r["books"][venue]["bids"] for r in rows], dtype=np.float64)
        ask = np.asarray([r["books"][venue]["asks"] for r in rows], dtype=np.float64)
        if np.any(np.diff(times) <= 0):
            raise ValueError("NON_CAUSAL_RECEIPTS")
        if not np.isfinite(bid).all() or not np.isfinite(ask).all() or np.any(bid <= 0) or np.any(ask <= 0):
            raise ValueError("INVALID_BOOK_NUMERICS")
        if np.any(np.diff(bid[:, :, 0], axis=1) >= 0) or np.any(np.diff(ask[:, :, 0], axis=1) <= 0):
            raise ValueError("INVALID_BOOK_ORDER")
        if np.any(bid[:, 0, 0] > ask[:, 0, 0]):
            raise ValueError("CROSSED_BOOK")
        books[venue] = {"times": times, "bids": bid, "asks": ask}
    unique_dates = sorted(set(dates))
    elapsed = (datetime.fromisoformat(unique_dates[-1]) - datetime.fromisoformat(unique_dates[0])).days + 1
    gate = prereg["causal_capture"]
    ready = (len(rows) >= gate["minimum_eligible_pairs"] and
             len(unique_dates) >= gate["minimum_distinct_observation_days"] and
             elapsed >= gate["minimum_elapsed_calendar_days"])
    return seconds, books, ready


def calculate(seconds, book, side, latency, percentages):
    times = book["times"]
    destination = np.searchsorted(times, times + latency, side="left")
    in_range = destination < len(times)
    eligible = np.zeros(len(times), dtype=bool)
    eligible[in_range] = seconds[destination[in_range]] <= seconds[in_range] + 1
    decisions = np.flatnonzero(eligible)
    executions = destination[eligible]
    side_levels = book["asks" if side == "BUY" else "bids"]
    liquidity = side_levels[decisions, :, 1].sum(axis=1)
    request = liquidity[:, None] * np.asarray(percentages)[None, :] / 100
    prices = side_levels[executions, :, 0]
    available = side_levels[executions, :, 1]
    # Prefix depth is independent of sequential remaining-quantity subtraction.
    prefix = np.concatenate((np.zeros((len(executions), 1)),
                             np.cumsum(available[:, :-1], axis=1)), axis=1)
    allocation = np.clip(request[:, :, None] - prefix[:, None, :], 0, available[:, None, :])
    filled = allocation.sum(axis=2)
    notional = (allocation * prices[:, None, :]).sum(axis=2)
    vwap = notional / filled
    remaining = np.maximum(request - filled, 0)
    sign = 1 if side == "BUY" else -1
    mid = (book["bids"][executions, 0, 0] + book["asks"][executions, 0, 0]) / 2
    best_slip = sign * (vwap / prices[:, 0, None] - 1) * 10000
    mid_slip = sign * (vwap / mid[:, None] - 1) * 10000
    monotonic = np.diff(vwap, axis=1) * sign
    scales = np.maximum(abs(vwap[:, 1:]), abs(vwap[:, :-1]))
    violations = int(np.count_nonzero(monotonic < -scales * 1e-12))
    return {
        "decisions": decisions, "executions": executions,
        "decision_receipts": times[decisions], "execution_receipts": times[executions],
        "request": request, "allocation": allocation, "prices": prices,
        "filled": filled, "notional": notional, "vwap": vwap, "remaining": remaining,
        "fill_rate": np.minimum(1, filled / request), "partial": remaining > request * 1e-12,
        "best_slip": best_slip, "mid_slip": mid_slip,
        "no_future": int(np.count_nonzero(~in_range)),
        "gap": int(np.count_nonzero(in_range & ~eligible)), "violations": violations,
    }


def scenario_key(obj):
    return tuple(obj[k] for k in ("venue", "side", "size_percent", "latency_ms", "fee_bps"))


def reproduce(rows, prereg, reference_events=None, tolerance=None):
    seconds, books, ready = validate(rows, prereg)
    grid = prereg["decision_to_execution_contract"]
    percentages = grid["virtual_order_size_grid_percent_of_observed_depth10_side_liquidity"]
    scenarios, counts = [], {"compared_events": 0, "event_mismatches": 0, "monotonicity_violations": 0}
    own_hash, reference_hash = hashlib.sha256(), hashlib.sha256()
    numeric = tolerance or {"relative": 1e-10, "absolute": 1e-8}
    def close(a, b):
        return bool(np.isfinite(a) and np.isfinite(b) and
                    abs(a - b) <= numeric["absolute"] + numeric["relative"] * max(abs(a), abs(b)))
    for venue in VENUES:
        for side in ("BUY", "SELL"):
            sign = 1 if side == "BUY" else -1
            for latency in grid["latency_ms_grid"]:
                out = calculate(seconds, books[venue], side, latency, percentages)
                counts["monotonicity_violations"] += out["violations"]
                for field in ("decisions", "executions", "request", "allocation", "vwap", "best_slip", "mid_slip"):
                    own_hash.update(out[field].tobytes())
                unavailable = {k: v for k, v in (("NO_CAUSAL_FUTURE_BOOK", out["no_future"]),
                                                ("OBSERVATION_GAP_ABSTAIN", out["gap"])) if v}
                n = len(out["decisions"])
                for k, pct in enumerate(percentages):
                    for fee in grid["fee_stress_bps_grid"]:
                        fee_values = out["notional"][:, k] * fee / 10000
                        partial = int(out["partial"][:, k].sum())
                        scenarios.append({
                            "venue": venue, "side": side, "size_percent": pct, "latency_ms": latency, "fee_bps": fee,
                            "effective_executions": n, "status": "EXECUTED" if n else "UNAVAILABLE",
                            "unavailable_reasons": unavailable, "partial_fills": partial, "full_fills": n - partial,
                            "fill_rate": float(out["fill_rate"][:, k].mean()) if n else None,
                            "mean_slippage_best_bps": float(out["best_slip"][:, k].mean()) if n else None,
                            "mean_slippage_mid_bps": float(out["mid_slip"][:, k].mean()) if n else None,
                            "total_fee_quote": float(fee_values.sum()),
                            "mean_effective_delay_ms": float((out["execution_receipts"] - out["decision_receipts"]).mean()) if n else None,
                        })
                if reference_events is None:
                    continue
                # The comparison reader follows the baseline's recorded event order.
                # No value from that file is used to compute this executor's fills.
                for i in range(n):
                    for k, pct in enumerate(percentages):
                        levels = [{"level": level + 1, "price": float(out["prices"][i, level]),
                                   "quantity": float(q)}
                                  for level, q in enumerate(out["allocation"][i, k]) if q > 0]
                        for fee in grid["fee_stress_bps_grid"]:
                            line = reference_events.readline()
                            if not line:
                                raise ValueError("REFERENCE_EVENTS_TRUNCATED")
                            reference_hash.update(line.encode())
                            event = json.loads(line)
                            key = (venue, side, pct, latency, fee)
                            mismatch = scenario_key(event) != key
                            mismatch |= event["decision_receipt_ms"] != int(out["decision_receipts"][i])
                            mismatch |= event["execution_receipt_ms"] != int(out["execution_receipts"][i])
                            expected = {
                                "requested_quantity": out["request"][i, k], "filled_quantity": out["filled"][i, k],
                                "unexecuted_quantity": out["remaining"][i, k], "fill_rate": out["fill_rate"][i, k],
                                "vwap": out["vwap"][i, k], "slippage_best_bps": out["best_slip"][i, k],
                                "slippage_mid_bps": out["mid_slip"][i, k],
                                "fee_quote": out["notional"][i, k] * fee / 10000,
                                "fee_adjusted_vwap": out["vwap"][i, k] * (1 + sign * fee / 10000),
                            }
                            mismatch |= any(not close(event[name], val) for name, val in expected.items())
                            mismatch |= event["partial_fill"] != bool(out["partial"][i, k])
                            observed_levels = event["fill_levels"]
                            # Numerical dust levels are ignored only below the fixed absolute tolerance.
                            observed_levels = [x for x in observed_levels if x["quantity"] > numeric["absolute"]]
                            expected_levels = [x for x in levels if x["quantity"] > numeric["absolute"]]
                            mismatch |= len(observed_levels) != len(expected_levels)
                            for actual, expected_level in zip(observed_levels, expected_levels):
                                mismatch |= actual["level"] != expected_level["level"]
                                mismatch |= not close(actual["price"], expected_level["price"])
                                mismatch |= not close(actual["quantity"], expected_level["quantity"])
                            counts["event_mismatches"] += int(mismatch)
                            counts["compared_events"] += 1
    if reference_events is not None and reference_events.readline():
        raise ValueError("REFERENCE_EVENTS_EXTRA")
    return {"scenarios": scenarios, "dataset_gate_ready": ready, **counts,
            "vector_execution_digest": own_hash.hexdigest(),
            "verified_reference_execution_digest": reference_hash.hexdigest() if reference_events else None}


def compare_scenarios(actual, expected, tolerances):
    if len(actual) != len(expected) or len({scenario_key(x) for x in expected}) != len(expected):
        raise ValueError("SCENARIO_COUNT_OR_DUPLICATE")
    indexed = {scenario_key(x): x for x in expected}
    errors = []
    exact = ("effective_executions", "status", "unavailable_reasons", "partial_fills", "full_fills")
    floating = ("fill_rate", "mean_slippage_best_bps", "mean_slippage_mid_bps",
                "total_fee_quote", "mean_effective_delay_ms")
    for row in actual:
        reference = indexed.get(scenario_key(row))
        if reference is None:
            errors.append({"scenario": scenario_key(row), "field": "missing"})
            continue
        for field in exact:
            if row[field] != reference[field]:
                errors.append({"scenario": scenario_key(row), "field": field})
        for field in floating:
            a, b = row[field], reference[field]
            if a is None or b is None:
                match = a is b
            else:
                match = bool(np.isfinite(a) and np.isfinite(b) and
                             abs(a - b) <= tolerances["absolute"] + tolerances["relative"] * max(abs(a), abs(b)))
            if not match:
                errors.append({"scenario": scenario_key(row), "field": field})
    return errors


def run(contract, prereg_path, ledger_path, report_path, fills_path):
    authority = json.loads(AUTHORITY.read_text())
    if contract != authority or contract["status"] != "FROZEN_IMPLEMENTATION_PARITY_CONTRACT":
        raise ValueError("FROZEN_CONTRACT_MISMATCH")
    prereg = json.loads(prereg_path.read_text())
    rows = [json.loads(line) for line in ledger_path.read_text().splitlines() if line.strip()]
    report = json.loads(report_path.read_text())
    bindings = {
        "dataset_semantic_sha256": digest(rows),
        "prereg_semantic_sha256": digest(prereg),
        "system11_report_semantic_sha256": digest(report),
        "system11_fills_sha256": file_hash(fills_path),
        "independent_executor_source_sha256": file_hash(Path(__file__)),
    }
    if any(contract["bindings"][k] != v for k, v in bindings.items()):
        raise ValueError("FROZEN_INPUT_OR_EXECUTOR_BINDING_MISMATCH")
    if report.get("system11_complete") is not True or report.get("status") != "PASS_FROZEN_LOB_STRESS_REPLAY":
        raise ValueError("SYSTEM11_NOT_COMPLETE")
    if report["dataset_sha256"] != bindings["dataset_semantic_sha256"] or report["prereg_sha256"] != bindings["prereg_semantic_sha256"]:
        raise ValueError("SYSTEM11_BINDING_MISMATCH")
    with gzip.open(fills_path, "rt", encoding="utf-8") as stream:
        result = reproduce(rows, prereg, stream, contract["event_tolerance"])
    repeat = reproduce(rows, prereg)
    errors = compare_scenarios(result["scenarios"], report["stressed_execution_results"], contract["scenario_tolerance"])
    checks = {
        "dataset_gate": result["dataset_gate_ready"],
        "reference_semantic_digest": result["verified_reference_execution_digest"] == report["execution_digest"],
        "all_events_compared": result["compared_events"] == sum(x["effective_executions"] for x in report["stressed_execution_results"]),
        "event_parity": result["event_mismatches"] == 0,
        "scenario_parity": not errors,
        "minimum_executions": all(x["effective_executions"] >= prereg["replay"]["minimum_effective_executions_per_primary_scenario"] for x in result["scenarios"]),
        "scenario_count": len(result["scenarios"]) == contract["required_scenario_count"],
        "deterministic_independent_executor": result["vector_execution_digest"] == repeat["vector_execution_digest"] and result["scenarios"] == repeat["scenarios"],
        "size_monotonicity": result["monotonicity_violations"] == 0,
    }
    return {
        "schema": "gate_btc.2_0.system12_implementation_replication.v1",
        "status": "PASS_IMPLEMENTATION_PARITY_PENDING_INDEPENDENT_ADJUDICATION" if all(checks.values()) else "FAIL_IMPLEMENTATION_PARITY",
        "system": 12, "independent_replication_executed": True,
        "implementation_replication_pass": all(checks.values()), "checks": checks,
        "system12_complete": False, "system13_dependency_released": False, "scientific_credit": 0,
        "independence_scope": contract["independence_scope"],
        "independent_adjudication_executed": False,
        "next_action": "INDEPENDENT_ADJUDICATION_OF_HASH_BOUND_IMPLEMENTATION_REPLICATION",
        "bindings": bindings, "contract_sha256": digest(contract),
        "numpy_version": np.__version__, "python_version": platform.python_version(),
        "compared_events": result["compared_events"], "event_mismatches": result["event_mismatches"],
        "scenario_mismatches": errors, "scenario_count": len(result["scenarios"]),
        "vector_execution_digest": result["vector_execution_digest"],
        "stressed_execution_results": result["scenarios"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True, "shadow_only": True, "orders": 0, "real_capital_brl": 0,
        "engine_feed": False, "automatic_promotion": False, "economic_claim_authorized": False,
        "no_backfill": True, "no_retune": True,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", type=Path, default=AUTHORITY)
    ap.add_argument("--prereg", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--system11-report", type=Path, required=True)
    ap.add_argument("--system11-fills", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = run(json.loads(args.contract.read_text()), args.prereg, args.ledger, args.system11_report, args.system11_fills)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(canonical({k: result[k] for k in ("status", "scenario_count", "compared_events", "event_mismatches", "system12_complete")}))
    return 0 if result["implementation_replication_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
