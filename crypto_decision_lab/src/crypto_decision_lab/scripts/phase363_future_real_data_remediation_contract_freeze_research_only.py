from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase359_path: Path, phase360_path: Path, phase361_path: Path, phase362_path: Path, output_dir: Path) -> dict[str, Any]:
    items=[read_json(x) for x in (phase359_path,phase360_path,phase361_path,phase362_path)]
    for phase,item in zip((359,360,361,362),items): validate_phase(item,phase)
    p359,p360,p361,p362=items; accepted=bool(p359.get("remediation_accepted_for_preregistration")); dry=bool(p361.get("dry_run_pass")) and bool(p362.get("dry_run_pass")); frozen=accepted and dry
    contract={"selected_remediation_id":p359.get("selected_remediation_id"),"preregistration_fingerprint":p360.get("preregistration_fingerprint"),"future_experiment_budget":int(p360.get("future_experiment_budget",0)),"success_criteria":p360.get("success_criteria",{}),"primary_metrics":p360.get("primary_metrics",[]),"one_evaluation_only":True,"closed_family_metrics_prohibited":True,"execution_metrics_prohibited":True}
    payload=base_payload(363,"FUTURE_REAL_DATA_REMEDIATION_CONTRACT_FROZEN_RESEARCH_ONLY" if frozen else "DATA_REMEDIATION_NO_GO_CONTRACT_RECORDED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE363_FUTURE_REAL_DATA_REMEDIATION_CONTRACT_FREEZE_READY_RESEARCH_ONLY","contract":contract,"contract_frozen":frozen,"contract_fingerprint":fingerprint(contract),"eligible_for_manual_future_execution_review":frozen,"real_data_remediation_evaluation_started":False,"public_collection_authorized":False,"public_collection_started":False,"closed_families_reopened":False,"next_decision":"MANUAL_REAL_DATA_REMEDIATION_EXECUTION_REVIEW_ONLY_RESEARCH_ONLY" if frozen else "DATA_REMEDIATION_NO_GO_PRESERVED_RESEARCH_ONLY"})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase363_future_real_data_remediation_contract_freeze.json",payload)
    write_summary(phase_summary(363,"future_real_data_remediation_contract_freeze"),title="Phase 363 — Future Real-data Remediation Contract Freeze",gate=payload["gate"],bullets=[f"Contract frozen: `{frozen}`",f"Future experiment budget: `{contract['future_experiment_budget']}`","Real-data evaluation started: `False`","Public collection authorized: `False`","Closed families reopened: `False`"])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    for phase,slug in [(359,"manual_data_remediation_decision"),(360,"finite_data_remediation_preregistration"),(361,"synthetic_data_remediation_contract_dry_run"),(362,"fixture_data_remediation_pipeline_dry_run")]: a.add_argument(f"--phase{phase}-artifact",type=Path,default=art/f"phase{phase}_{slug}_research_only"/f"phase{phase}_{slug}.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase363_future_real_data_remediation_contract_freeze_research_only")
    x=a.parse_args(); p=build(x.phase359_artifact,x.phase360_artifact,x.phase361_artifact,x.phase362_artifact,x.output_dir); print(p["gate"]); print("Contract frozen:",p["contract_frozen"]); return 0
if __name__=="__main__": raise SystemExit(main())
