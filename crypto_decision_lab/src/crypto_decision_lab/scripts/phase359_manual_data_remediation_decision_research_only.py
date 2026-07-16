from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, VALID_REMEDIATION_DECISIONS, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase356_path: Path, phase357_path: Path, phase358_path: Path, decision: str, reviewer_label: str, output_dir: Path) -> dict[str, Any]:
    p356,p357,p358=read_json(phase356_path),read_json(phase357_path),read_json(phase358_path)
    validate_phase(p356,356); validate_phase(p357,357); validate_phase(p358,358)
    normalized=decision.strip().upper()
    if normalized not in VALID_REMEDIATION_DECISIONS: raise RuntimeError(f"Decision must be one of {VALID_REMEDIATION_DECISIONS}.")
    deriv_ok=bool(p357.get("material_improvement_feasible_without_private_api")); align_ok=bool(p358.get("material_improvement_feasible_with_existing_data"))
    recommendation="ACCEPT_TIMESTAMP_CONSENSUS" if align_ok else ("ACCEPT_DERIVATIVES_COVERAGE" if deriv_ok else "REJECT_ALL")
    selected=None; accepted=False; effective="REJECT_ALL_DATA_REMEDIATION_RESEARCH_ONLY"
    if normalized=="ACCEPT_TIMESTAMP_CONSENSUS" and align_ok:
        selected="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1"; accepted=True; effective="ACCEPT_ONE_TIMESTAMP_CONSENSUS_REMEDIATION_FOR_PREREGISTRATION_ONLY_RESEARCH_ONLY"
    elif normalized=="ACCEPT_DERIVATIVES_COVERAGE" and deriv_ok:
        selected="PUBLIC_DERIVATIVES_COVERAGE_REMEDIATION_V1"; accepted=True; effective="ACCEPT_ONE_PUBLIC_DERIVATIVES_REMEDIATION_FOR_PREREGISTRATION_ONLY_RESEARCH_ONLY"
    elif normalized!="REJECT_ALL":
        effective="REJECT_SELECTED_REMEDIATION_FAILED_FEASIBILITY_GATES_RESEARCH_ONLY"
    payload=base_payload(359,"MANUAL_DATA_REMEDIATION_DECISION_RECORDED_RESEARCH_ONLY")
    payload.update({
        "gate":"PHASE359_MANUAL_DATA_REMEDIATION_DECISION_READY_RESEARCH_ONLY",
        "selected_decision":normalized,"effective_decision":effective,"reviewer_label":reviewer_label.strip() or "UNSPECIFIED_LOCAL_REVIEWER",
        "decision_source":"EXPLICIT_LOCAL_CONSOLE_INPUT","audit_recommendation":recommendation,
        "remediation_accepted_for_preregistration":accepted,"selected_remediation_id":selected,
        "acceptance_scope":"ONE_DATA_ENGINEERING_REMEDIATION_CONTRACT_ONLY" if accepted else "NONE",
        "acceptance_does_not_reopen_closed_families":True,"acceptance_does_not_authorize_strategy_testing":True,
        "acceptance_does_not_authorize_public_collection":True,"acceptance_does_not_authorize_execution":True,
        "experiment_budget_open":False,"historical_remediation_evaluation_started":False,"new_family_opened":False,
    })
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase359_manual_data_remediation_decision.json",payload)
    write_summary(phase_summary(359,"manual_data_remediation_decision"),title="Phase 359 — Manual Data-remediation Decision",gate=payload["gate"],bullets=[
        f"Selected decision: `{normalized}`",f"Audit recommendation: `{recommendation}`",f"Accepted for preregistration: `{accepted}`",f"Selected remediation: `{selected or 'NONE'}`","Closed families reopened: `False`",
    ])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    a.add_argument("--phase356-artifact",type=Path,default=art/"phase356_manual_data_remediation_backlog_freeze_research_only/phase356_manual_data_remediation_backlog_freeze.json")
    a.add_argument("--phase357-artifact",type=Path,default=art/"phase357_public_derivatives_coverage_feasibility_research_only/phase357_public_derivatives_coverage_feasibility.json")
    a.add_argument("--phase358-artifact",type=Path,default=art/"phase358_timestamp_consensus_alignment_feasibility_research_only/phase358_timestamp_consensus_alignment_feasibility.json")
    a.add_argument("--decision",choices=VALID_REMEDIATION_DECISIONS,required=True); a.add_argument("--reviewer-label",default="Victor Sardinha")
    a.add_argument("--output-dir",type=Path,default=art/"phase359_manual_data_remediation_decision_research_only")
    x=a.parse_args(); p=build(x.phase356_artifact,x.phase357_artifact,x.phase358_artifact,x.decision,x.reviewer_label,x.output_dir); print(p["gate"]); print("Effective decision:",p["effective_decision"]); return 0
if __name__=="__main__": raise SystemExit(main())
