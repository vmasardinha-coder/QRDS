from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase351_path: Path, phase355_path: Path, output_dir: Path) -> dict[str, Any]:
    p351, p355 = read_json(phase351_path), read_json(phase355_path)
    validate_phase(p351, 351); validate_phase(p355, 355)
    if p355.get("next_window_decision") != "DATA_REMEDIATION_OR_GENUINELY_NEW_QUESTION_MANUAL_REVIEW_ONLY_RESEARCH_ONLY":
        raise RuntimeError("Phase 355 did not authorize manual data-remediation review.")
    items = [
        {
            "question_id": "PUBLIC_DERIVATIVES_COVERAGE_REMEDIATION_V1",
            "source_backlog_item": "FUNDING_OI_COVERAGE_DIAGNOSTIC",
            "scope": "PUBLIC_NO_AUTH_DATA_ENGINEERING_ONLY",
            "eligible_for_feasibility_audit": True,
            "collection_authorized": False,
            "closed_family_rescue_allowed": False,
        },
        {
            "question_id": "TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1",
            "source_backlog_item": "PROVIDER_TIMESTAMP_ALIGNMENT_DIAGNOSTIC",
            "scope": "EXISTING_PUBLIC_DATA_ENGINEERING_ONLY",
            "eligible_for_feasibility_audit": True,
            "collection_authorized": False,
            "closed_family_rescue_allowed": False,
        },
    ]
    payload = base_payload(356, "MANUAL_DATA_REMEDIATION_BACKLOG_FROZEN_RESEARCH_ONLY")
    payload.update({
        "gate": "PHASE356_MANUAL_DATA_REMEDIATION_BACKLOG_FREEZE_READY_RESEARCH_ONLY",
        "frozen_backlog": items,
        "frozen_backlog_count": len(items),
        "private_data_item_prohibited": True,
        "selected_experiment": None,
        "experiment_budget_open": False,
        "public_collection_started": False,
        "closed_families_reopened": False,
        "decision": "TWO_DATA_REMEDIATION_QUESTIONS_FROZEN_FOR_FEASIBILITY_ONLY_RESEARCH_ONLY",
    })
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True); write_json(output_dir / "phase356_manual_data_remediation_backlog_freeze.json", payload)
    write_summary(phase_summary(356, "manual_data_remediation_backlog_freeze"), title="Phase 356 — Manual Data-remediation Backlog Freeze", gate=payload["gate"], bullets=[
        "Frozen remediation questions: `2`", "Collection authorized: `False`", "Experiment budget open: `False`", "Closed families reopened: `False`",
    ])
    return payload


def main() -> int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    a.add_argument("--phase351-artifact",type=Path,default=art/"phase351_data_remediation_decision_research_only/phase351_data_remediation_decision.json")
    a.add_argument("--phase355-artifact",type=Path,default=art/"phase355_negative_evidence_navigation_checkpoint_research_only/phase355_negative_evidence_navigation_checkpoint.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase356_manual_data_remediation_backlog_freeze_research_only")
    x=a.parse_args(); p=build(x.phase351_artifact,x.phase355_artifact,x.output_dir); print(p["gate"]); print("Frozen questions:",p["frozen_backlog_count"]); return 0
if __name__=="__main__": raise SystemExit(main())
