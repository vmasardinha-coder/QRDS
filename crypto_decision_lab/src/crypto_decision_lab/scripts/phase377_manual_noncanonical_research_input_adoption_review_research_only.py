from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import ADOPTION_DECISIONS, ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary

def build(phase367_path:Path,phase376_path:Path,output_dir:Path,*,decision:str,reviewer_label:str)->dict[str,Any]:
    if decision not in ADOPTION_DECISIONS: raise RuntimeError(f"Invalid adoption decision: {decision}")
    p367=read_json(phase367_path); p376=read_json(phase376_path); validate_phase(p367,367); validate_phase(p376,376)
    eligible=(p376.get("data_quality_contract_pass") is True and p376.get("governance_pass") is True and p367.get("evaluation_executed") is True and bool(p367.get("remediated_dataset_path")) and bool(p367.get("remediated_dataset_sha256")))
    approved=eligible and decision=="ADOPT_AS_NONCANONICAL_RESEARCH_INPUT_ONLY"
    payload=base_payload(377,"NONCANONICAL_RESEARCH_INPUT_ADOPTION_REVIEW_COMPLETE_RESEARCH_ONLY")
    payload.update({"gate":"PHASE377_MANUAL_NONCANONICAL_RESEARCH_INPUT_ADOPTION_REVIEW_READY_RESEARCH_ONLY","reviewer_label":reviewer_label,"decision_source":"EXPLICIT_USER_DELEGATION_2026_07_16","selected_decision":decision,"review_eligible":eligible,"candidate_adoption_approved":approved,"canonical_adoption_approved":False,"strategy_use_approved":False,"closed_family_retest_authorized":False,"selected_evaluation_id":p367.get("evaluation_id"),"candidate_dataset_path":p367.get("remediated_dataset_path"),"candidate_dataset_sha256":p367.get("remediated_dataset_sha256"),"approved_scope":"NONCANONICAL_RESEARCH_INPUT_METADATA_REGISTRY_ONLY" if approved else "NONE","canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase377_manual_noncanonical_research_input_adoption_review.json",payload)
    write_summary(phase_summary(377,"manual_noncanonical_research_input_adoption_review"),title="Phase 377 — Manual Noncanonical Research-input Adoption Review",gate=payload["gate"],bullets=[f"Decision: `{decision}`",f"Eligible: `{eligible}`",f"Candidate adoption approved: `{approved}`","Canonical adoption approved: `False`","Strategy use approved: `False`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase367-artifact",type=Path,default=art/"phase367_one_real_data_remediation_evaluation_research_only/phase367_one_real_data_remediation_evaluation.json"); a.add_argument("--phase376-artifact",type=Path,default=art/"phase376_successful_data_quality_remediation_result_registry_research_only/phase376_successful_data_quality_remediation_result_registry.json"); a.add_argument("--decision",choices=ADOPTION_DECISIONS,required=True); a.add_argument("--reviewer-label",default="Victor Sardinha"); a.add_argument("--output-dir",type=Path,default=art/"phase377_manual_noncanonical_research_input_adoption_review_research_only"); x=a.parse_args(); p=build(x.phase367_artifact,x.phase376_artifact,x.output_dir,decision=x.decision,reviewer_label=x.reviewer_label); print(p["gate"]); print("Decision:",p["selected_decision"]); return 0
if __name__=="__main__": raise SystemExit(main())
