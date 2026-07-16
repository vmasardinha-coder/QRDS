from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase366_375_remediation_evaluation_common import (
    ROOT,
    VALID_EXECUTION_REVIEW_DECISIONS,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(
    phase363_path: Path,
    phase365_path: Path,
    decision: str,
    reviewer_label: str,
    output_dir: Path,
) -> dict[str, Any]:
    p363 = read_json(phase363_path)
    p365 = read_json(phase365_path)
    validate_phase(p363, 363)
    validate_phase(p365, 365)

    normalized = decision.strip().upper()
    if normalized not in VALID_EXECUTION_REVIEW_DECISIONS:
        raise RuntimeError(f"Decision must be one of {VALID_EXECUTION_REVIEW_DECISIONS}.")

    contract = dict(p363.get("contract", {}))
    frozen = bool(p363.get("contract_frozen"))
    selected = contract.get("selected_remediation_id")
    eligible = (
        frozen
        and selected == "TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1"
        and int(contract.get("future_experiment_budget", 0)) == 1
        and contract.get("one_evaluation_only") is True
        and contract.get("closed_family_metrics_prohibited") is True
        and contract.get("execution_metrics_prohibited") is True
        and p365.get("real_data_remediation_evaluation_started") is False
        and int(p365.get("active_hypotheses", 0)) == 0
    )
    approved = normalized == "APPROVE_ONE_FROZEN_REMEDIATION_EVALUATION" and eligible
    effective = (
        "APPROVE_EXACTLY_ONE_FROZEN_DATA_QUALITY_EVALUATION_RESEARCH_ONLY"
        if approved
        else "REJECT_REAL_DATA_REMEDIATION_EVALUATION_RESEARCH_ONLY"
    )

    payload = base_payload(366, "MANUAL_FROZEN_REMEDIATION_EXECUTION_REVIEW_RECORDED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE366_MANUAL_FROZEN_REMEDIATION_EXECUTION_REVIEW_READY_RESEARCH_ONLY",
            "selected_decision": normalized,
            "effective_decision": effective,
            "reviewer_label": reviewer_label.strip() or "UNSPECIFIED_LOCAL_REVIEWER",
            "decision_source": "EXPLICIT_LOCAL_CONSOLE_INPUT",
            "contract_frozen": frozen,
            "contract_fingerprint": p363.get("contract_fingerprint"),
            "selected_remediation_id": selected,
            "contract_review_eligible": eligible,
            "one_real_data_quality_evaluation_approved": approved,
            "approved_scope": "ONE_DATA_QUALITY_EVALUATION_ONLY" if approved else "NONE",
            "strategy_metric_authorized": False,
            "closed_family_retest_authorized": False,
            "public_collection_authorized": False,
            "execution_authorized": False,
            "active_hypotheses": 0,
            "active_experiment_budget": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase366_manual_frozen_remediation_execution_review.json", payload)
    write_summary(
        phase_summary(366, "manual_frozen_remediation_execution_review"),
        title="Phase 366 — Manual Frozen-remediation Execution Review",
        gate=payload["gate"],
        bullets=[
            f"Decision: `{normalized}`",
            f"Contract review eligible: `{eligible}`",
            f"One data-quality evaluation approved: `{approved}`",
            "Strategy metrics authorized: `False`",
            "Capital authorized: `R$ 0`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    parser.add_argument(
        "--phase363-artifact",
        type=Path,
        default=art
        / "phase363_future_real_data_remediation_contract_freeze_research_only"
        / "phase363_future_real_data_remediation_contract_freeze.json",
    )
    parser.add_argument(
        "--phase365-artifact",
        type=Path,
        default=art
        / "phase365_data_remediation_full_integration_checkpoint_research_only"
        / "phase365_data_remediation_full_integration_checkpoint.json",
    )
    parser.add_argument("--decision", choices=VALID_EXECUTION_REVIEW_DECISIONS, required=True)
    parser.add_argument("--reviewer-label", default="Victor Sardinha")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase366_manual_frozen_remediation_execution_review_research_only",
    )
    args = parser.parse_args()
    payload = build(
        args.phase363_artifact,
        args.phase365_artifact,
        args.decision,
        args.reviewer_label,
        args.output_dir,
    )
    print(payload["gate"])
    print("Effective decision:", payload["effective_decision"])
    print("One data-quality evaluation approved:", payload["one_real_data_quality_evaluation_approved"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
