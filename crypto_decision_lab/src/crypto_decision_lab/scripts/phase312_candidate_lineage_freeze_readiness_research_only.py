from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    artifact_identity,
    base_payload,
    fingerprint,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


def build(
    phase304_path: Path,
    phase306_path: Path,
    phase307_path: Path,
    phase308_path: Path,
    phase309_path: Path,
    phase310_path: Path,
    phase311_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    paths = {
        304: phase304_path,
        306: phase306_path,
        307: phase307_path,
        308: phase308_path,
        309: phase309_path,
        310: phase310_path,
        311: phase311_path,
    }
    payloads: dict[int, dict[str, Any]] = {}
    lineage: list[dict[str, Any]] = []
    for phase, path in paths.items():
        item = read_json(path)
        validate_phase(item, phase)
        payloads[phase] = item
        lineage.append(artifact_identity(path, item))

    phase311 = payloads[311]
    candidate_eligible = bool(phase311.get("candidate_eligible"))
    candidate_id = phase311.get("candidate_hypothesis_id")
    lineage_complete = all(entry["sha256"] and entry["gate"] for entry in lineage)
    freeze_readiness = candidate_eligible and lineage_complete
    freeze_created = False
    freeze_status = (
        "ELIGIBLE_AWAITING_EXPLICIT_MANUAL_SCIENTIFIC_REVIEW"
        if freeze_readiness
        else "NOT_FROZEN_NO_ELIGIBLE_CANDIDATE"
    )

    payload = base_payload(312, "CANDIDATE_LINEAGE_FREEZE_READINESS_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE312_CANDIDATE_LINEAGE_FREEZE_READINESS_READY_RESEARCH_ONLY",
            "candidate_hypothesis_id": candidate_id,
            "candidate_eligible": candidate_eligible,
            "lineage": lineage,
            "lineage_complete": lineage_complete,
            "eligibility_contract_fingerprint": phase311.get("eligibility_contract_fingerprint"),
            "freeze_readiness": freeze_readiness,
            "freeze_created": freeze_created,
            "freeze_id": None,
            "freeze_status": freeze_status,
            "manual_scientific_review_required": True,
            "automatic_freeze_allowed": False,
            "automatic_promotion_allowed": False,
            "historical_result_can_start_clock": False,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
        }
    )
    payload["lineage_fingerprint"] = fingerprint(lineage)
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase312_candidate_lineage_freeze_readiness.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase312_candidate_lineage_freeze_readiness_summary.md",
        title="Phase 312 — Candidate Lineage and Freeze Readiness",
        gate=payload["gate"],
        bullets=[
            f"Candidate hypothesis: `{candidate_id}`",
            f"Candidate eligible: `{candidate_eligible}`",
            f"Lineage artifacts verified: `{len(lineage)}`",
            f"Lineage complete: `{lineage_complete}`",
            f"Freeze readiness: `{freeze_readiness}`",
            f"Freeze created: `{freeze_created}`",
            f"Freeze status: `{freeze_status}`",
            "Manual scientific review required: `True`",
            "Automatic freeze allowed: `False`",
            "Historical result can start forward clock: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    artifacts = ROOT / "artifacts"
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase304-artifact", type=Path, default=artifacts / "phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json")
    parser.add_argument("--phase306-artifact", type=Path, default=artifacts / "phase306_temporal_selection_stability_audit_research_only/phase306_temporal_selection_stability_audit.json")
    parser.add_argument("--phase307-artifact", type=Path, default=artifacts / "phase307_regime_concentration_audit_research_only/phase307_regime_concentration_audit.json")
    parser.add_argument("--phase308-artifact", type=Path, default=artifacts / "phase308_hypothesis_dependence_audit_research_only/phase308_hypothesis_dependence_audit.json")
    parser.add_argument("--phase309-artifact", type=Path, default=artifacts / "phase309_extreme_cost_liquidity_audit_research_only/phase309_extreme_cost_liquidity_audit.json")
    parser.add_argument("--phase310-artifact", type=Path, default=artifacts / "phase310_timestamp_sensitivity_audit_research_only/phase310_timestamp_sensitivity_audit.json")
    parser.add_argument("--phase311-artifact", type=Path, default=artifacts / "phase311_candidate_eligibility_contract_v2_research_only/phase311_candidate_eligibility_contract_v2.json")
    parser.add_argument("--output-dir", type=Path, default=artifacts / "phase312_candidate_lineage_freeze_readiness_research_only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(
        args.phase304_artifact,
        args.phase306_artifact,
        args.phase307_artifact,
        args.phase308_artifact,
        args.phase309_artifact,
        args.phase310_artifact,
        args.phase311_artifact,
        args.output_dir,
    )
    print(payload["gate"])
    print("Candidate eligible:", payload["candidate_eligible"])
    print("Lineage complete:", payload["lineage_complete"])
    print("Freeze readiness:", payload["freeze_readiness"])
    print("Freeze created:", payload["freeze_created"])
    print("Freeze status:", payload["freeze_status"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
