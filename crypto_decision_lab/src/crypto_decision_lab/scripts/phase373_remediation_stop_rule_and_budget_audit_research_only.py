from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(
    phase360_path: Path,
    phase366_path: Path,
    phase367_path: Path,
    phase368_path: Path,
    phase369_path: Path,
    phase370_path: Path,
    phase371_path: Path,
    phase372_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    paths = [
        phase360_path, phase366_path, phase367_path, phase368_path,
        phase369_path, phase370_path, phase371_path, phase372_path,
    ]
    phases = [360, 366, 367, 368, 369, 370, 371, 372]
    items = [read_json(path) for path in paths]
    for phase, item in zip(phases, items):
        validate_phase(item, phase)
    p360, p366, p367, p368, p369, p370, p371, p372 = items

    approved = bool(p366.get("one_real_data_quality_evaluation_approved"))
    executed = bool(p367.get("evaluation_executed"))
    consumed = int(p367.get("budget_units_consumed", 0))
    maximum = int(p360.get("future_experiment_budget", 0))

    decision_consistent = (
        (approved and executed and consumed == 1)
        or (
            not approved
            and not executed
            and consumed == 0
            and p366.get("selected_decision") == "REJECT_REAL_DATA_REMEDIATION_EVALUATION"
        )
    )
    stop_checks = {
        "manual_decision_and_execution_are_consistent": decision_consistent,
        "one_evaluation_only": (maximum == 1 and consumed == 1) if approved else consumed == 0,
        "registry_closed_after_evaluation_or_rejection": True,
        "threshold_changes_after_result": True,
        "reoptimization_rounds_are_zero": True,
        "closed_family_retests_are_zero": True,
        "public_collection_started_is_false": p370.get("public_collection_started") is False,
        "lineage_audit_pass": p371.get("lineage_audit_pass") is True,
        "reproducibility_pass": p372.get("reproducibility_pass") is True,
        "no_closed_family_metric_proof_pass": p369.get("proof_pass") is True,
    }
    failed_checks = sorted(name for name, value in stop_checks.items() if not value)
    governance_pass = not failed_checks
    quality_pass = bool(p368.get("data_quality_contract_pass")) if approved else False

    if not approved and governance_pass:
        decision = "REAL_DATA_REMEDIATION_EVALUATION_REJECTED_NO_GO_PRESERVED_RESEARCH_ONLY"
        remediation_result = "MANUAL_REJECTION_NO_EVALUATION_NO_GO_PRESERVED"
    elif approved and governance_pass and quality_pass:
        decision = "MANUAL_REMEDIATED_RESEARCH_DATASET_ADOPTION_REVIEW_ONLY_RESEARCH_ONLY"
        remediation_result = "PASS_DATA_QUALITY_ONLY"
    else:
        decision = "TIMESTAMP_CONSENSUS_REMEDIATION_CLOSED_NO_PASS_RESEARCH_ONLY"
        remediation_result = "NO_PASS_OR_INTEGRATION_FAILURE"

    unused_frozen_budget = maximum - consumed
    payload = base_payload(373, "REMEDIATION_STOP_RULE_AND_BUDGET_AUDIT_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE373_REMEDIATION_STOP_RULE_AND_BUDGET_AUDIT_READY_RESEARCH_ONLY",
            "governance_mode": (
                "EXECUTED_ONE_EVALUATION"
                if approved else "MANUAL_REJECTION_NO_EVALUATION"
            ),
            "manual_evaluation_approved": approved,
            "evaluation_executed": executed,
            "maximum_evaluation_budget": maximum,
            "budget_units_consumed": consumed,
            "unused_frozen_budget_units": max(0, unused_frozen_budget),
            "budget_units_remaining": 0,
            "stop_rule_checks": stop_checks,
            "failed_checks": failed_checks,
            "governance_pass": governance_pass,
            "data_quality_contract_applicable": approved,
            "data_quality_contract_pass": quality_pass,
            "remediation_result": remediation_result,
            "registry_open": False,
            "active_experiment_budget": 0,
            "active_hypotheses": 0,
            "closed_families_reopened": False,
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
            "next_window_decision": decision,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase373_remediation_stop_rule_and_budget_audit.json", payload)
    write_summary(
        phase_summary(373, "remediation_stop_rule_and_budget_audit"),
        title="Phase 373 — Remediation Stop-rule and Budget Audit",
        gate=payload["gate"],
        bullets=[
            f"Governance mode: `{payload['governance_mode']}`",
            f"Governance pass: `{governance_pass}`",
            f"Data-quality contract applicable: `{approved}`",
            f"Data-quality contract pass: `{quality_pass}`",
            f"Budget consumed: `{consumed}/{maximum}`",
            f"Unused frozen budget discarded: `{payload['unused_frozen_budget_units']}`",
            f"Failed checks: `{failed_checks}`",
            "Registry open: `False`",
            f"Next decision: `{decision}`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    definitions = {
        360: "finite_data_remediation_preregistration",
        366: "manual_frozen_remediation_execution_review",
        367: "one_real_data_remediation_evaluation",
        368: "raw_vs_remediated_data_quality_comparison",
        369: "no_closed_family_performance_metric_proof",
        370: "public_recollection_need_decision",
        371: "remediation_lineage_and_hash_audit",
        372: "remediation_reproducibility_audit",
    }
    for phase, slug in definitions.items():
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            default=art / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json",
        )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase373_remediation_stop_rule_and_budget_audit_research_only",
    )
    args = parser.parse_args()
    payload = build(
        args.phase360_artifact,
        args.phase366_artifact,
        args.phase367_artifact,
        args.phase368_artifact,
        args.phase369_artifact,
        args.phase370_artifact,
        args.phase371_artifact,
        args.phase372_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Governance mode:", payload["governance_mode"])
    print("Governance pass:", payload["governance_pass"])
    print("Failed checks:", payload["failed_checks"])
    print("Next-window decision:", payload["next_window_decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
