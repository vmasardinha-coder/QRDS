#!/usr/bin/env python3
"""Read-only System12 prerequisite binding. Never awards replication credit."""
import argparse
import hashlib
import json
from pathlib import Path

from gate_btc_2_system11_collection_status import status as collection_status
from gate_btc_2_system11_stress_replay_v1 import AUTHORITY, digest, validate_pairs


def assess(report, rows):
    result = {"schema": "gate_btc.2_0.system12_readiness.v1", "system": 12,
        "system12_complete": False, "system13_dependency_released": False,
        "scientific_credit": 0, "independent_replication_executed": False,
        "upstream_system11_ready": False, "research_only": True, "shadow_only": True,
        "orders": 0, "real_capital_brl": 0, "engine_feed": False,
        "no_backfill": True, "no_retune": True, "automatic_promotion": False,
        "structural_harness_available": True}
    if report is None:
        return {**result, "status": "BLOCKED_MISSING_SYSTEM11_REPORT"}
    result["system11_report_sha256"] = digest(report)
    if report.get("system11_complete") is not True or report.get("status") != "PASS_FROZEN_LOB_STRESS_REPLAY":
        return {**result, "status": "BLOCKED_UPSTREAM_SYSTEM11_INCOMPLETE"}
    if rows is None:
        return {**result, "status": "BLOCKED_MISSING_HASH_BOUND_SYSTEM11_LEDGER"}
    prereg = json.loads(AUTHORITY.read_text())
    try:
        validate_pairs(rows)
        grid = prereg["decision_to_execution_contract"]
        expected = {(v, s, pct, latency, fee) for v in prereg["venues"] for s in ("BUY", "SELL")
            for pct in grid["virtual_order_size_grid_percent_of_observed_depth10_side_liquidity"]
            for latency in grid["latency_ms_grid"] for fee in grid["fee_stress_bps_grid"]}
        scenarios = report["stressed_execution_results"]
        actual = [(x["venue"], x["side"], x["size_percent"], x["latency_ms"], x["fee_bps"]) for x in scenarios]
        checks = {
            "dataset_hash": report["dataset_sha256"] == digest(rows),
            "prereg_hash": report["prereg_sha256"] == digest(prereg),
            "dataset_gate": collection_status(prereg, rows)["dataset_gate_ready"],
            "scenario_grid": len(actual) == len(expected) and set(actual) == expected,
            "minimum_executions": all(x["status"] == "EXECUTED" and x["effective_executions"] >= prereg["replay"]["minimum_effective_executions_per_primary_scenario"] for x in scenarios),
            "deterministic": report["deterministic_replay_pass"] is True,
            "causal": report["causal_integrity_pass"] is True,
            "observed_fills": report["fills_explainable_by_observed_depth10"] is True,
            "monotonicity": report["size_impact"]["violations"] == 0,
            "fill_artifact_receipt": bool(report["fill_level_artifacts"]["sha256"]) and report["fill_level_artifacts"]["semantic_digest"] == report["execution_digest"],
            "source_binding": report["engine_and_version_provenance"]["engine_source_sha256"] == hashlib.sha256((AUTHORITY.parents[2] / "tools/gate_btc_2_system11_stress_replay_v1.py").read_bytes()).hexdigest(),
            "safety": report["orders"] == 0 and report["real_capital_brl"] == 0 and report["engine_feed"] is False and report["research_only"] is True and report["shadow_only"] is True,
        }
    except (KeyError, ValueError, TypeError, OSError) as exc:
        return {**result, "status": "BLOCKED_INVALID_SYSTEM11_EVIDENCE", "error": str(exc)}
    ready = all(checks.values())
    return {**result, "upstream_system11_ready": ready, "upstream_checks": checks,
        "status": "STRUCTURAL_READY_PENDING_FROZEN_INDEPENDENT_REPLICATION_CONTRACT" if ready else "BLOCKED_INVALID_SYSTEM11_EVIDENCE",
        "next_action": "BIND_INDEPENDENT_REPLICATION_CONTRACT_WITHOUT_AUTO_COMPLETION" if ready else "WAIT_FOR_VALID_SYSTEM11_COMPLETION"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system11-report", type=Path, required=True)
    ap.add_argument("--system11-ledger", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    report = json.loads(a.system11_report.read_text()) if a.system11_report.exists() else None
    rows = [json.loads(x) for x in a.system11_ledger.read_text().splitlines() if x.strip()] if a.system11_ledger.exists() else None
    result = assess(report, rows)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
