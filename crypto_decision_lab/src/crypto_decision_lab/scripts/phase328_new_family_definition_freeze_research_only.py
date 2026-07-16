from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase326_335_preregistration_common import (
    PROPOSED_NEW_FAMILY_ID,
    PROPOSED_QUESTION_ID,
    QUESTION,
    ROOT,
    base_payload,
    canonical_hash,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(
    phase323_path: Path,
    phase327_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase323 = read_json(phase323_path)
    phase327 = read_json(phase327_path)
    validate_phase(phase323, 323)
    validate_phase(phase327, 327)
    accepted = (
        phase323.get("preregistration_draft_created") is True
        and phase327.get("question_accepted_for_preregistration") is True
    )
    contract = {
        "family_id": PROPOSED_NEW_FAMILY_ID,
        "question_id": PROPOSED_QUESTION_ID,
        "scientific_question": QUESTION,
        "purpose": "RESEARCH_WHEN_TO_ABSTAIN_OR_EVALUATE_ONLY",
        "allowed_output": ["RESEARCH_ABSTAIN", "RESEARCH_EVALUATE"],
        "prohibited_outputs": [
            "BUY",
            "SELL",
            "LONG",
            "SHORT",
            "ALLOCATE",
            "ORDER",
            "POSITION_SIZE",
        ],
        "directional_return_target_allowed": False,
        "automatic_family_opening_allowed": False,
        "historical_evaluation_allowed_in_phase328": False,
        "execution_allowed": False,
    }
    definition_frozen = accepted
    state = (
        "FAMILY_DEFINITION_FROZEN_RESEARCH_ONLY"
        if definition_frozen
        else "FAMILY_DEFINITION_NOT_FROZEN_REJECTED_OR_BLOCKED"
    )
    payload = base_payload(328, state)
    payload.update(
        {
            "gate": "PHASE328_NEW_FAMILY_DEFINITION_FREEZE_READY_RESEARCH_ONLY",
            "question_accepted": accepted,
            "family_definition_frozen": definition_frozen,
            "family_definition_state": state,
            "family_definition_contract": contract if definition_frozen else None,
            "family_definition_sha256": (
                canonical_hash(contract) if definition_frozen else None
            ),
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
        output_dir / "phase328_new_family_definition_freeze.json",
        payload,
    )
    write_summary(
        ROOT
        / "docs/reports/preregistration_v2/"
        "phase328_new_family_definition_freeze_summary.md",
        title="Phase 328 — New-family Definition Freeze",
        gate=payload["gate"],
        bullets=[
            f"Question accepted: `{accepted}`",
            f"Family definition frozen: `{definition_frozen}`",
            f"State: `{state}`",
            "New family opened: `False`",
            "Hypotheses registered: `0`",
            "Historical evaluation started: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    artifacts = ROOT / "artifacts"
    parser.add_argument(
        "--phase323-artifact",
        type=Path,
        default=artifacts
        / "phase323_new_family_preregistration_contract_research_only/"
        "phase323_new_family_preregistration_contract.json",
    )
    parser.add_argument(
        "--phase327-artifact",
        type=Path,
        default=artifacts
        / "phase327_manual_scientific_question_decision_contract_research_only/"
        "phase327_manual_scientific_question_decision_contract.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=artifacts
        / "phase328_new_family_definition_freeze_research_only",
    )
    args = parser.parse_args()
    payload = build(
        args.phase323_artifact,
        args.phase327_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Family definition frozen:", payload["family_definition_frozen"])
    print("New family opened:", payload["new_family_opened"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
