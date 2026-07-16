from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    PROPOSED_NEW_FAMILY_ID,
    PROPOSED_QUESTION_ID,
    ROOT,
    base_payload,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)

VALID_DECISIONS = ("ACCEPT", "REJECT")


def build(
    phase326_path: Path,
    decision: str,
    reviewer_label: str,
    output_dir: Path,
) -> dict[str, Any]:
    phase326 = read_json(phase326_path)
    validate_phase(phase326, 326)
    normalized = decision.strip().upper()
    if normalized not in VALID_DECISIONS:
        raise RuntimeError(
            f"Manual decision must be one of {VALID_DECISIONS}, got {decision!r}."
        )
    recommendation_allows_acceptance = (
        phase326.get("review_recommendation")
        == "ACCEPT_QUESTION_FOR_PREREGISTRATION_REVIEW_ONLY"
        and phase326.get("failed_review_gate_count") == 0
    )
    accepted = normalized == "ACCEPT" and recommendation_allows_acceptance
    if normalized == "ACCEPT" and not recommendation_allows_acceptance:
        effective_decision = "REJECT_BLOCKED_BY_FAILED_REVIEW_GATES"
    elif accepted:
        effective_decision = "ACCEPT_QUESTION_ONLY_FOR_PREREGISTRATION_RESEARCH_ONLY"
    else:
        effective_decision = "REJECT_QUESTION_RESEARCH_ONLY"

    payload = base_payload(
        327,
        "MANUAL_SCIENTIFIC_QUESTION_DECISION_RECORDED_RESEARCH_ONLY",
    )
    payload.update(
        {
            "gate": "PHASE327_MANUAL_SCIENTIFIC_QUESTION_DECISION_CONTRACT_READY_RESEARCH_ONLY",
            "question_id": PROPOSED_QUESTION_ID,
            "family_id": PROPOSED_NEW_FAMILY_ID,
            "selected_decision": normalized,
            "effective_decision": effective_decision,
            "reviewer_label": reviewer_label.strip() or "UNSPECIFIED_LOCAL_REVIEWER",
            "decision_source": "EXPLICIT_LOCAL_CONSOLE_INPUT",
            "question_accepted_for_preregistration": accepted,
            "question_rejected": not accepted,
            "acceptance_scope": (
                "QUESTION_AND_PREREGISTRATION_CONTRACT_ONLY"
                if accepted
                else "NONE"
            ),
            "acceptance_does_not_open_family": True,
            "acceptance_does_not_open_budget": True,
            "acceptance_does_not_authorize_historical_evaluation": True,
            "acceptance_does_not_authorize_execution": True,
            "new_family_opened": False,
            "hypotheses_registered": 0,
            "experiment_budget_opened": False,
            "historical_evaluation_started": False,
            "strategy_approved": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "phase327_manual_scientific_question_decision_contract.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase327_manual_scientific_question_decision_contract_summary.md",
        title="Phase 327 — Manual Scientific-question Decision Contract",
        gate=payload["gate"],
        bullets=[
            f"Selected decision: `{normalized}`",
            f"Effective decision: `{effective_decision}`",
            f"Question accepted for preregistration: `{accepted}`",
            "New family opened: `False`",
            "Experiment budget opened: `False`",
            "Historical evaluation started: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument(
        "--phase326-artifact",
        type=Path,
        default=artifacts
        / "phase326_human_readable_novelty_non_overlap_review_research_only/"
        "phase326_human_readable_novelty_non_overlap_review.json",
    )
    parser.add_argument("--decision", choices=VALID_DECISIONS, required=True)
    parser.add_argument("--reviewer-label", default="Victor Sardinha")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase327_manual_scientific_question_decision_contract_research_only",
    )
    args = parser.parse_args()
    payload = build(
        args.phase326_artifact,
        args.decision,
        args.reviewer_label,
        args.output_dir,
    )
    print(payload["gate"])
    print("Effective decision:", payload["effective_decision"])
    print(
        "Question accepted:",
        payload["question_accepted_for_preregistration"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
