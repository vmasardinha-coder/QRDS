from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import ROOT, base_payload, fingerprint, phase_summary, read_json, resolve_recorded_path, sha256_file, validate_phase, write_json, write_summary

def build(phase367_path:Path,phase379_path:Path,phase381_path:Path,output_dir:Path,*,project_root:Path|None=None)->dict[str,Any]:
    p367=read_json(phase367_path); p379=read_json(phase379_path); p381=read_json(phase381_path)
    for phase,p in ((367,p367),(379,p379),(381,p381)): validate_phase(p,phase)
    root=(project_root or ROOT).resolve(); raw_results=[]
    for item in p367.get("input_lineage",[]):
        path=resolve_recorded_path(root,item.get("path")); exists=path is not None and path.is_file(); actual=sha256_file(path) if exists else None; raw_results.append({"provider":item.get("provider"),"recorded_path":item.get("path"),"exists":exists,"expected_sha256":item.get("sha256"),"actual_sha256":actual,"verified":exists and actual==item.get("sha256")})
    candidate_path=resolve_recorded_path(root,p379.get("candidate_contract",{}).get("candidate_dataset_path"))
    candidate_under_artifacts=(candidate_path is not None and "artifacts" in candidate_path.parts)
    checks={"integrity_pass":p381.get("integrity_pass") is True,"raw_lineage_nonempty":len(raw_results)>=3,"all_raw_inputs_preserved":bool(raw_results) and all(item["verified"] for item in raw_results),"candidate_coexists_under_artifacts":candidate_under_artifacts,"rollback_metadata_only":p379.get("candidate_contract",{}).get("rollback_method")=="REMOVE_METADATA_REGISTRY_REFERENCE_ONLY","canonical_writes_zero":p379.get("candidate_contract",{}).get("canonical_data_writes")==0}
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 382 rollback/coexistence audit failed; failed_checks={failed!r}.")
    payload=base_payload(382,"ROLLBACK_AND_RAW_COEXISTENCE_AUDIT_PASS_RESEARCH_ONLY"); payload.update({"gate":"PHASE382_ROLLBACK_AND_RAW_COEXISTENCE_AUDIT_READY_RESEARCH_ONLY","coexistence_checks":checks,"failed_checks":[],"coexistence_pass":True,"rollback_ready":True,"raw_input_count":len(raw_results),"raw_lineage_verification":raw_results,"candidate_file_deleted":False,"raw_files_modified":False,"canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase382_rollback_and_raw_coexistence_audit.json",payload)
    write_summary(phase_summary(382,"rollback_and_raw_coexistence_audit"),title="Phase 382 — Rollback and Raw-data Coexistence Audit",gate=payload["gate"],bullets=["Coexistence pass: `True`","Rollback ready: `True`",f"Raw inputs verified: `{len(raw_results)}`","Raw files modified: `False`","Canonical writes: `0`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase367-artifact",type=Path,default=art/"phase367_one_real_data_remediation_evaluation_research_only/phase367_one_real_data_remediation_evaluation.json"); a.add_argument("--phase379-artifact",type=Path,default=art/"phase379_noncanonical_research_dataset_schema_and_lineage_contract_research_only/phase379_noncanonical_research_dataset_schema_and_lineage_contract.json"); a.add_argument("--phase381-artifact",type=Path,default=art/"phase381_noncanonical_research_dataset_integrity_audit_research_only/phase381_noncanonical_research_dataset_integrity_audit.json"); a.add_argument("--output-dir",type=Path,default=art/"phase382_rollback_and_raw_coexistence_audit_research_only"); x=a.parse_args(); p=build(x.phase367_artifact,x.phase379_artifact,x.phase381_artifact,x.output_dir); print(p["gate"]); print("Rollback ready:",p["rollback_ready"]); return 0
if __name__=="__main__": raise SystemExit(main())
