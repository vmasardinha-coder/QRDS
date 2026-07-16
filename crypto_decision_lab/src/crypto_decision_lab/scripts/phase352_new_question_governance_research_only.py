from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)

REQUIRED_REVIEW_GATES = (
    "MATERIALLY_DIFFERENT_FROM_CLOSED_DIRECTIONAL_FAMILY",
    "MATERIALLY_DIFFERENT_FROM_CLOSED_ABSTENTION_FAMILY",
    "NON_DIRECTIONAL_OR_EXPLICITLY_RESEARCH_ONLY",
    "FINITE_BUDGET_DEFINED_BEFORE_RESULTS",
    "LABEL_AVAILABLE_WITHOUT_FUTURE_LEAKAGE",
    "NO_PRIVATE_API_OR_ACCOUNT_DEPENDENCY",
    "CLEAR_NULL_MODEL_AND_STOP_RULE",
    "HUMAN_ACCEPT_OR_REJECT_DECISION",
)


def build(phase350_path: Path, phase351_path: Path, output_dir: Path) -> dict[str, Any]:
    p350 = read_json(phase350_path)
    p351 = read_json(phase351_path)
    validate_phase(p350, 350)
    validate_phase(p351, 351)
    if p350.get("closure_sealed") is not True or p351.get("data_remediation_reopens_family") is not False:
        raise RuntimeError("Closure or remediation governance is inconsistent.")

    gates = [
        {
            "gate_id": gate_id,
            "status": "REQUIRED_FOR_ANY_FUTURE_PROPOSAL",
            "waiver_allowed": False,
        }
        for gate_id in REQUIRED_REVIEW_GATES
    ]
    payload = base_payload(352, "NEW_QUESTION_GOVERNANCE_READY_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE352_NEW_QUESTION_GOVERNANCE_READY_RESEARCH_ONLY",
            "required_review_gates": gates,
            "required_review_gate_count": len(gates),
            "new_question_proposed": False,
            "new_family_opened": False,
            "new_hypotheses_registered": 0,
            "new_experiment_budget": 0,
            "automatic_question_generation_allowed": False,
            "decision": "MANUAL_NEW_QUESTION_OR_DATA_REMEDIATION_REVIEW_ONLY_RESEARCH_ONLY",
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase352_new_question_governance.json", payload)
    write_summary(
        phase_summary(352, "new_question_governance"),
        title="Phase 352 — New-question Governance",
        gate=payload["gate"],
        bullets=[
            f"Required future review gates: `{payload['required_review_gate_count']}`",
            "New question proposed: `False`",
            "New family opened: `False`",
            "New hypotheses registered: `0`",
            "Automatic question generation allowed: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase350-artifact", type=Path, default=ROOT / "artifacts/phase350_abstention_closure_integrity_seal_research_only/phase350_abstention_closure_integrity_seal.json")
    parser.add_argument("--phase351-artifact", type=Path, default=ROOT / "artifacts/phase351_data_remediation_decision_research_only/phase351_data_remediation_decision.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase352_new_question_governance_research_only")
    args = parser.parse_args()
    payload = build(args.phase350_artifact, args.phase351_artifact, args.output_dir)
    print(payload["gate"])
    print("New family opened:", payload["new_family_opened"])
    print("Decision:", payload["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
