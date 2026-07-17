from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary

def build(phase375_path: Path, output_dir: Path) -> dict[str, Any]:
    p375=read_json(phase375_path); validate_phase(p375,375)
    checks={
        "quality_evaluation_executed":p375.get("evaluation_executed") is True,
        "data_quality_contract_pass":p375.get("data_quality_contract_pass") is True,
        "governance_pass":p375.get("governance_pass") is True,
        "closed_family_metric_unused":p375.get("no_closed_family_metric_proof_pass") is True,
        "candidate_not_previously_adopted":p375.get("candidate_research_dataset_adopted",False) is False,
        "canonical_writes_zero":p375.get("locks",{}).get("canonical_data_writes")==0,
        "active_hypotheses_zero":int(p375.get("active_hypotheses",-1))==0,
        "active_budget_zero":int(p375.get("active_experiment_budget",-1))==0,
    }
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 376 entry checks failed; failed_checks={failed!r}.")
    payload=base_payload(376,"SUCCESSFUL_DATA_QUALITY_REMEDIATION_RESULT_REGISTERED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE376_SUCCESSFUL_DATA_QUALITY_REMEDIATION_RESULT_REGISTRY_READY_RESEARCH_ONLY","entry_checks":checks,"failed_checks":[],"evaluation_id":p375.get("evaluation_id"),"real_historical_rows_used":int(p375.get("real_historical_rows_used",0)),"provider_dataset_count":int(p375.get("provider_dataset_count",0)),"data_quality_contract_pass":True,"governance_pass":True,"candidate_dataset_adopted":False,"canonical_data_writes":0,"next_decision":"MANUAL_NONCANONICAL_RESEARCH_INPUT_ADOPTION_REVIEW_ONLY"})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase376_successful_data_quality_remediation_result_registry.json",payload)
    write_summary(phase_summary(376,"successful_data_quality_remediation_result_registry"),title="Phase 376 — Successful Data-quality Remediation Result Registry",gate=payload["gate"],bullets=[f"Historical rows used: `{payload['real_historical_rows_used']}`",f"Provider datasets: `{payload['provider_dataset_count']}`","Candidate adopted: `False`","Canonical data writes: `0`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase375-artifact",type=Path,default=art/"phase375_data_quality_remediation_integrated_checkpoint_research_only/phase375_data_quality_remediation_integrated_checkpoint.json"); a.add_argument("--output-dir",type=Path,default=art/"phase376_successful_data_quality_remediation_result_registry_research_only"); x=a.parse_args(); p=build(x.phase375_artifact,x.output_dir); print(p["gate"]); print("Candidate adopted:",p["candidate_dataset_adopted"]); return 0
if __name__=="__main__": raise SystemExit(main())
