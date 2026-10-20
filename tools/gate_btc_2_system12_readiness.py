#!/usr/bin/env python3
"""Read-only System12 prerequisite binding. Never awards replication credit."""
import argparse
import hashlib
import json
from pathlib import Path

from gate_btc_2_system11_collection_status import status as collection_status
from gate_btc_2_system11_stress_replay_v1 import AUTHORITY, digest, validate_pairs

from gate_btc_system12_post_review_release import RELEASE_AUTHORITY, retain_post_review_release

REPLICATION_AUTHORITY = Path(__file__).resolve().parents[1] / "artifacts/gate_btc_2/SYSTEM12_IMPLEMENTATION_REPLICATION_V1_20261010.json"
ADJUDICATION_AUTHORITY = Path(__file__).resolve().parents[1] / "artifacts/gate_btc_2/separate_reviews_20261019/SISTEMA12_PARECER.json"
ADJUDICATION_SEMANTIC_SHA256 = "00ae74518d9e391c90d7cf0cff7ac59a2004c5f3d79f7ccc360ff8032df56a12"
REPLICATION_CHECKS = ("dataset_gate", "reference_semantic_digest", "all_events_compared",
    "event_parity", "scenario_parity", "minimum_executions", "scenario_count",
    "deterministic_independent_executor", "size_monotonicity")


def retain_replication_progress(structural, contract, replication):
    """Bind a frozen receipt for reporting; never adjudicate or transfer its scope."""
    result = {**structural, "replication_continuity_status": "NO_HASH_BOUND_REPLICATION_RECEIPT",
        "system12_complete": False, "system13_dependency_released": False,
        "independent_adjudication_executed": False, "scientific_credit": 0,
        "orders": 0, "real_capital_brl": 0, "engine_feed": False, "automatic_promotion": False}
    if contract is None or replication is None:
        return result
    try:
        frozen = json.loads(REPLICATION_AUTHORITY.read_text())
        scenarios = replication["stressed_execution_results"]
        count = replication["compared_events"]
        counts = [s["effective_executions"] for s in scenarios]
        valid = (
            contract == frozen
            and replication["contract_sha256"] == digest(frozen)
            and replication["bindings"] == frozen["bindings"]
            and replication["status"] == "PASS_IMPLEMENTATION_PARITY_PENDING_INDEPENDENT_ADJUDICATION"
            and replication["implementation_replication_pass"] is True
            and replication["independent_replication_executed"] is True
            and all(replication["checks"][k] is True for k in REPLICATION_CHECKS)
            and replication["scenario_count"] == frozen["required_scenario_count"] == len(scenarios)
            and type(count) is int and count > 0
            and all(type(n) is int and n >= 0 for n in counts) and sum(counts) == count
            and type(replication["event_mismatches"]) is int and replication["event_mismatches"] == 0
            and replication["scenario_mismatches"] == []
            and all(replication[k] is False for k in ("system12_complete", "system13_dependency_released",
                "independent_adjudication_executed", "engine_feed", "automatic_promotion", "economic_claim_authorized"))
            and all(type(replication[k]) is int and replication[k] == 0 for k in ("scientific_credit", "orders", "real_capital_brl"))
            and replication["research_only"] is True and replication["shadow_only"] is True
        )
    except (KeyError, TypeError, ValueError, OSError):
        valid = False
    if not valid:
        return {**result, "replication_continuity_status": "INVALID_FROZEN_REPLICATION_RECEIPT",
            "status": "BLOCKED_INVALID_FROZEN_REPLICATION_RECEIPT",
            "next_action": "VERIFY_EXACT_FROZEN_RECEIPT_BINDINGS_WITHOUT_REFREEZE"}
    result.update({
        "replication_continuity_status": "VERIFIED_FROZEN_IMPLEMENTATION_PARITY_RECEIPT",
        "frozen_implementation_replication_pass": True,
        "frozen_replication_contract_sha256": digest(frozen),
        "frozen_replication_bindings": replication["bindings"],
        "frozen_compared_events": count,
        "frozen_scenario_count": len(scenarios),
        "independent_adjudication_required": True,
        "replication_scope": "FROZEN_CONTRACT_ONLY_NO_TRANSFER_TO_NEW_COLLECTION",
        "current_upstream_report_matches_frozen_replication": structural.get("system11_report_sha256") == frozen["bindings"]["system11_report_semantic_sha256"],
    })
    if structural.get("upstream_system11_ready") is True:
        result.update({"status": "IMPLEMENTATION_PARITY_PASSED_PENDING_INDEPENDENT_ADJUDICATION",
            "next_action": "INDEPENDENT_ADJUDICATION_OF_EXISTING_HASH_BOUND_REPLICATION"})
    return result


def retain_adjudication_progress(result, contract, review):
    """Report the separate frozen-scope decision; never activate or release systems."""
    out = {**result, "adjudication_receipt_status": "NOT_PROVIDED",
        "independent_adjudication_executed": False}
    if review is None:
        return out
    try:
        effect = review["operational_effect"]
        valid = (
            digest(review) == ADJUDICATION_SEMANTIC_SHA256
            and contract == json.loads(REPLICATION_AUTHORITY.read_text())
            and review["contract_semantic_sha256"] == digest(contract)
            and review["subjects"]["bindings"] == contract["bindings"]
            and review["scope"] == contract["scope"]
            and review["decision"] == "PASS"
            and review["independent_adjudication_executed"] is True
            and review["implementation_parity_adjudication_pass"] is True
            and review["blocking_limitations"] == []
            and review["adjudicator"]["canonical_task"] == "/root/revisao_sistema12"
            and all(effect[k] is False for k in (
                "system12_complete", "system13_dependency_released",
                "system12_completion_authorized", "system13_release_authorized", "engine_feed"))
            and all(type(effect[k]) is int and effect[k] == 0
                    for k in ("scientific_credit", "orders", "real_capital_brl"))
        )
    except (KeyError, TypeError, ValueError, OSError):
        valid = False
    if not valid:
        return {**out, "adjudication_receipt_status": "INVALID",
            "status": "BLOCKED_INVALID_INDEPENDENT_ADJUDICATION_RECEIPT",
            "next_action": "VERIFY_PINNED_ADJUDICATION_WITHOUT_CHANGING_FROZEN_SUBJECTS"}
    if result.get("replication_continuity_status") != "VERIFIED_FROZEN_IMPLEMENTATION_PARITY_RECEIPT":
        return {**out, "adjudication_receipt_status": "VALID_REVIEW_MISSING_VALID_REPLICATION"}
    out.update({
        "adjudication_receipt_status": "VERIFIED_SEPARATE_AGENT_ADJUDICATION",
        "independent_adjudication_executed": True,
        "adjudication_decision": "PASS",
        "adjudication_receipt_semantic_sha256": digest(review),
        "adjudication_scope": review["scope"],
        "adjudicator": review["adjudicator"],
        "adjudication_issued_at_utc": review["issued_at_utc"],
        "adjudicated_bindings": review["subjects"]["bindings"],
        "system12_complete": False, "system13_dependency_released": False,
        "system12_completion_authorized": False, "system13_release_authorized": False,
        "scientific_credit": 0, "orders": 0, "real_capital_brl": 0,
        "engine_feed": False, "automatic_promotion": False,
    })
    if result.get("upstream_system11_ready") is True:
        out.update({"status": "FROZEN_PARITY_ADJUDICATED_PENDING_FORMAL_RELEASE",
            "next_action": "BIND_EXPLICIT_POST_REVIEW_RELEASE_WITHOUT_REFREEZE"})
    return out


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
    ap.add_argument("--implementation-contract", type=Path)
    ap.add_argument("--implementation-replication", type=Path)
    ap.add_argument("--independent-adjudication", type=Path, default=ADJUDICATION_AUTHORITY)
    ap.add_argument("--post-review-release", type=Path, default=RELEASE_AUTHORITY)
    a = ap.parse_args()
    if bool(a.implementation_contract) != bool(a.implementation_replication):
        ap.error("implementation contract and replication must be supplied together")
    report = json.loads(a.system11_report.read_text()) if a.system11_report.exists() else None
    rows = [json.loads(x) for x in a.system11_ledger.read_text().splitlines() if x.strip()] if a.system11_ledger.exists() else None
    result = assess(report, rows)
    if a.implementation_contract:
        contract = json.loads(a.implementation_contract.read_text()) if a.implementation_contract.exists() else None
        replication = json.loads(a.implementation_replication.read_text()) if a.implementation_replication.exists() else None
        result = retain_replication_progress(result, contract, replication)
        review = json.loads(a.independent_adjudication.read_text(encoding="utf-8")) if a.independent_adjudication.exists() else None
        result = retain_adjudication_progress(result, contract, review)
        release = json.loads(a.post_review_release.read_text(encoding="utf-8")) if a.post_review_release.exists() else None
        result = retain_post_review_release(result, contract, review, release)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

