from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase346_355_closure_navigation_common import (
    FAMILY_ID,
    ROOT,
    base_payload,
    fingerprint,
    phase_summary,
    read_json,
    validate_phase,
    write_json,
    write_summary,
)

CATEGORY_MAP = {
    "HOLM_PRIMARY_SUCCESS": "MULTIPLE_TESTING_NO_SURVIVOR",
    "CALIBRATION_VALIDATED": "CALIBRATION_FAILURE",
    "ROBUST_ACROSS_STRATA": "REGIME_OR_PROVIDER_ROBUSTNESS_FAILURE",
    "COVERAGE_RELIABILITY_PASS": "COVERAGE_RELIABILITY_TRADEOFF_FAILURE",
    "OUTER_HOLDOUT_UNTOUCHED": "OUTER_HOLDOUT_INTEGRITY_FAILURE",
}


def build(phase346_path: Path, phase343_path: Path, output_dir: Path) -> dict[str, Any]:
    p346 = read_json(phase346_path)
    p343 = read_json(phase343_path)
    validate_phase(p346, 346)
    validate_phase(p343, 343)

    counts: dict[str, int] = {}
    template_failures: dict[str, list[str]] = {}
    for template_id, record in p343.get("template_gate_records", {}).items():
        categories: list[str] = []
        for gate in record.get("gates", []):
            if gate.get("passed") is False:
                gate_id = str(gate.get("gate_id", "UNKNOWN"))
                category = CATEGORY_MAP.get(gate_id, f"GATE_FAILURE_{gate_id}")
                counts[category] = counts.get(category, 0) + 1
                categories.append(category)
        template_failures[str(template_id)] = sorted(set(categories))

    if not counts:
        raise RuntimeError("No failure causes were found for a family closed with no survivors.")

    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    payload = base_payload(348, "ABSTENTION_FAILURE_CAUSES_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE348_ABSTENTION_FAILURE_CAUSE_AUDIT_READY_RESEARCH_ONLY",
            "family_id": FAMILY_ID,
            "failure_category_counts": dict(ordered),
            "failure_category_count": len(ordered),
            "template_failure_categories": template_failures,
            "dominant_failure_category": ordered[0][0],
            "parameter_rescue_recommended": False,
            "scientific_classification": "NEGATIVE_RESULT_NOT_SOFTWARE_FAILURE",
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase348_abstention_failure_cause_audit.json", payload)
    write_summary(
        phase_summary(348, "abstention_failure_cause_audit"),
        title="Phase 348 — Abstention Failure-cause Audit",
        gate=payload["gate"],
        bullets=[
            f"Failure categories: `{payload['failure_category_count']}`",
            f"Dominant category: `{payload['dominant_failure_category']}`",
            "Scientific classification: `NEGATIVE_RESULT_NOT_SOFTWARE_FAILURE`",
            "Parameter rescue recommended: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase346-artifact", type=Path, default=ROOT / "artifacts/phase346_abstention_negative_evidence_registration_research_only/phase346_abstention_negative_evidence_registration.json")
    parser.add_argument("--phase343-artifact", type=Path, default=ROOT / "artifacts/phase343_research_candidate_eligibility_research_only/phase343_research_candidate_eligibility.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/phase348_abstention_failure_cause_audit_research_only")
    args = parser.parse_args()
    payload = build(args.phase346_artifact, args.phase343_artifact, args.output_dir)
    print(payload["gate"])
    print("Failure categories:", payload["failure_category_count"])
    print("Dominant category:", payload["dominant_failure_category"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
