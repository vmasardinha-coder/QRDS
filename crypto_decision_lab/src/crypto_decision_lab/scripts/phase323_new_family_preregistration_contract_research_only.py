from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import PROPOSED_NEW_FAMILY_ID, ROOT, base_payload, fingerprint, read_json, validate_phase, write_json, write_summary

def build(phase317_path:Path,phase322_path:Path,output_dir:Path)->dict[str,Any]:
    p317,p322=read_json(phase317_path),read_json(phase322_path); validate_phase(p317,317); validate_phase(p322,322)
    justified=p322.get("genuinely_different_question_justified") is True
    contract={
      "family_id":PROPOSED_NEW_FAMILY_ID,"state":"DRAFT_AWAITING_MANUAL_REVIEW" if justified else "NOT_CREATED_NO_JUSTIFICATION",
      "scientific_question_id":p322.get("proposed_question_id"),"scientific_question":p322.get("proposed_scientific_question"),
      "target":"FUTURE_MODEL_ERROR_OR_INSTABILITY_ABSTENTION_LABEL","directional_return_target_allowed":False,
      "maximum_hypothesis_budget_if_later_manually_opened":12,"current_registered_hypotheses":0,"current_experiment_budget":0,
      "multiple_testing_method_if_opened":"HOLM_BONFERRONI","nested_walk_forward_required":True,"outer_data_selection_allowed":False,
      "closed_family_signature_reference":p317.get("closed_family_signature_sha256"),"prohibited_signature_count":p317.get("prohibited_signature_count"),
      "manual_approval_required_before_opening":True,"automatic_opening_allowed":False,"execution_allowed":False,
    }
    payload=base_payload(323,"NEW_FAMILY_PREREGISTRATION_DRAFTED_RESEARCH_ONLY" if justified else "NEW_FAMILY_PREREGISTRATION_NOT_JUSTIFIED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE323_NEW_FAMILY_PREREGISTRATION_CONTRACT_READY_RESEARCH_ONLY","preregistration_draft_created":justified,"preregistration_contract":contract,"new_family_opened":False,"hypotheses_registered":0,"experiment_budget_opened":False,"manual_review_required":justified,"strategy_approved":False,"forward_shadow_eligible":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase323_new_family_preregistration_contract.json",payload)
    write_summary(ROOT/"docs/reports/new_family_preregistration/phase323_new_family_preregistration_contract_summary.md",title="Phase 323 — New-Family Pre-registration Contract",gate=payload["gate"],bullets=[f"Draft created: `{justified}`",f"Proposed family: `{PROPOSED_NEW_FAMILY_ID}`","New family opened: `False`","Hypotheses registered: `0`","Experiment budget opened: `False`","Manual approval required before any future opening."])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase317-artifact",type=Path,default=art/"phase317_prohibited_retest_signature_registry_research_only/phase317_prohibited_retest_signature_registry.json"); a.add_argument("--phase322-artifact",type=Path,default=art/"phase322_new_scientific_question_novelty_audit_research_only/phase322_new_scientific_question_novelty_audit.json"); a.add_argument("--output-dir",type=Path,default=art/"phase323_new_family_preregistration_contract_research_only"); x=a.parse_args(); p=build(x.phase317_artifact,x.phase322_artifact,x.output_dir); print(p["gate"]); print("Draft created:",p["preregistration_draft_created"]); print("New family opened:",p["new_family_opened"]); return 0
if __name__=="__main__": raise SystemExit(main())
