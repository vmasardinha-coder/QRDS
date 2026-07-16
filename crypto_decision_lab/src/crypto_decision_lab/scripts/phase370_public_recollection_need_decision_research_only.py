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


def build(phase367_path: Path, phase368_path: Path, phase369_path: Path, output_dir: Path) -> dict[str, Any]:
    p367 = read_json(phase367_path)
    p368 = read_json(phase368_path)
    p369 = read_json(phase369_path)
    validate_phase(p367, 367)
    validate_phase(p368, 368)
    validate_phase(p369, 369)

    executed = bool(p367.get("evaluation_executed"))
    proof_pass = bool(p369.get("proof_pass"))

    if not executed:
        skip_consistent = (
            p367.get("skip_reason") == "MANUAL_EXECUTION_REVIEW_REJECTED"
            and p368.get("manual_rejection_no_go_preserved") is True
            and proof_pass
        )
        enough_existing_data = False
        contract_pass = False
        recollection_applicable = False
        recollection_needed = False
        decision = (
            "NO_PUBLIC_RECOLLECTION_EVALUATION_REJECTED_RESEARCH_ONLY"
            if skip_consistent
            else "MANUAL_SCHEMA_REVIEW_REQUIRED_SKIPPED_PATH_INCONSISTENT_RESEARCH_ONLY"
        )
    else:
        enough_existing_data = (
            int(p367.get("provider_dataset_count", 0)) >= 3
            and int(p367.get("metrics", {}).get("TOTAL_UNION_HOURS", 0)) >= 720
        )
        contract_pass = bool(p368.get("data_quality_contract_pass"))
        recollection_applicable = True
        recollection_needed = not (enough_existing_data and contract_pass and proof_pass)
        decision = (
            "NO_PUBLIC_RECOLLECTION_REQUIRED_EXISTING_DATA_SUFFICIENT_RESEARCH_ONLY"
            if not recollection_needed
            else "MANUAL_PUBLIC_RECOLLECTION_REVIEW_REQUIRED_RESEARCH_ONLY"
        )

    payload = base_payload(370, "PUBLIC_RECOLLECTION_NEED_DECISION_RECORDED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE370_PUBLIC_RECOLLECTION_NEED_DECISION_READY_RESEARCH_ONLY",
            "evaluation_executed": executed,
            "recollection_assessment_applicable": recollection_applicable,
            "existing_provider_dataset_count": int(p367.get("provider_dataset_count", 0)),
            "existing_union_hours": int(p367.get("metrics", {}).get("TOTAL_UNION_HOURS", 0)),
            "existing_data_sufficient": enough_existing_data,
            "data_quality_contract_pass": contract_pass,
            "no_closed_family_metric_proof_pass": proof_pass,
            "public_recollection_needed": recollection_needed,
            "decision": decision,
            "public_collection_authorized": False,
            "public_collection_started": False,
            "silent_network_action_allowed": False,
            "private_api_allowed": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase370_public_recollection_need_decision.json", payload)
    write_summary(
        phase_summary(370, "public_recollection_need_decision"),
        title="Phase 370 — Public Recollection Need Decision",
        gate=payload["gate"],
        bullets=[
            f"Evaluation executed: `{executed}`",
            f"Recollection assessment applicable: `{recollection_applicable}`",
            f"Public recollection needed: `{recollection_needed}`",
            f"Decision: `{decision}`",
            "Public collection authorized: `False`",
            "Silent network action allowed: `False`",
        ],
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    art = ROOT / "artifacts"
    for phase, slug in (
        (367, "one_real_data_remediation_evaluation"),
        (368, "raw_vs_remediated_data_quality_comparison"),
        (369, "no_closed_family_performance_metric_proof"),
    ):
        parser.add_argument(
            f"--phase{phase}-artifact",
            type=Path,
            default=art / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json",
        )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=art / "phase370_public_recollection_need_decision_research_only",
    )
    args = parser.parse_args()
    payload = build(args.phase367_artifact, args.phase368_artifact, args.phase369_artifact, args.output_dir)
    print(payload["gate"])
    print("Decision:", payload["decision"])
    print("Public collection started:", payload["public_collection_started"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
