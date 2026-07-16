from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    FAMILY_ID,
    ROOT,
    base_payload,
    fingerprint,
    phase_artifact,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)


def build(phase345_path: Path, phase343_path: Path, output_dir: Path) -> dict[str, Any]:
    p345 = read_json(phase345_path)
    p343 = read_json(phase343_path)
    validate_phase(p345, 345)
    validate_phase(p343, 343)
    if p345.get("next_window_decision") != "ABSTENTION_FAMILY_CLOSED_NO_SURVIVOR_RESEARCH_ONLY":
        raise RuntimeError("Phase 345 did not enter the no-survivor closure path.")
    if int(p345.get("eligible_template_count", -1)) != 0 or p345.get("historical_research_candidate_id"):
        raise RuntimeError("Phase 345 unexpectedly contains an eligible historical candidate.")

    failed_gate_counts: dict[str, int] = {}
    for record in p343.get("template_gate_records", {}).values():
        for gate in record.get("gates", []):
            if gate.get("passed") is False:
                gate_id = str(gate.get("gate_id", "UNKNOWN"))
                failed_gate_counts[gate_id] = failed_gate_counts.get(gate_id, 0) + 1

    payload = base_payload(346, "ABSTENTION_NEGATIVE_EVIDENCE_REGISTERED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE346_ABSTENTION_NEGATIVE_EVIDENCE_REGISTRY_READY_RESEARCH_ONLY",
            "family_id": FAMILY_ID,
            "historical_rows": int(p345.get("historical_rows", 0)),
            "evaluated_template_count": int(p345.get("template_count", 0)),
            "holm_survivor_count": int(p345.get("holm_survivor_count", 0)),
            "robust_template_count": int(p345.get("robust_template_count", 0)),
            "eligible_template_count": int(p345.get("eligible_template_count", 0)),
            "family_decision": "CLOSE_ABSTENTION_FAMILY_NO_SURVIVOR_RESEARCH_ONLY",
            "negative_evidence_registered": True,
            "negative_evidence_reversible": False,
            "failed_gate_counts": failed_gate_counts,
            "candidate_freeze_created": False,
            "forward_evidence_clock_started": False,
            "forward_evidence_credit": 0,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase346_abstention_negative_evidence_registration.json", payload)
    write_summary(
        phase_summary(346, "abstention_negative_evidence_registration"),
        title="Phase 346 — Abstention Negative-evidence Registration",
        gate=payload["gate"],
        bullets=[
            f"Family: `{FAMILY_ID}`",
            f"Templates evaluated: `{payload['evaluated_template_count']}`",
            f"Holm survivors: `{payload['holm_survivor_count']}`",
            f"Final eligible templates: `{payload['eligible_template_count']}`",
            "Negative evidence registered permanently: `True`",
            "Historical result cannot authorize execution: `True`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase345-artifact", type=Path, default=ROOT / "artifacts/phase345_abstention_full_integration_checkpoint_research_only/phase345_abstention_full_integration_checkpoint.json")
    parser.add_argument("--phase343-artifact", type=Path, default=ROOT / "artifacts/phase343_research_candidate_eligibility_research_only/phase343_research_candidate_eligibility.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase346_abstention_negative_evidence_registration_research_only")
    args = parser.parse_args()
    payload = build(args.phase345_artifact, args.phase343_artifact, args.output_dir)
    print(payload["gate"])
    print("Negative evidence registered:", payload["negative_evidence_registered"])
    print("Eligible templates:", payload["eligible_template_count"])
    print("Action:", payload["locks"]["action_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
