from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import CANDIDATE_SCHEMA, ROOT, base_payload, fingerprint, phase_summary, read_json, resolve_recorded_path, sha256_file, stream_candidate_rows, validate_phase, write_json, write_summary

def build(phase367_path:Path,phase379_path:Path,phase380_path:Path,output_dir:Path,*,project_root:Path|None=None)->dict[str,Any]:
    p367=read_json(phase367_path); p379=read_json(phase379_path); p380=read_json(phase380_path)
    for phase,p in ((367,p367),(379,p379),(380,p380)): validate_phase(p,phase)
    contract=p379.get("candidate_contract",{}); root=(project_root or ROOT).resolve(); path=resolve_recorded_path(root,contract.get("candidate_dataset_path")); expected=contract.get("candidate_dataset_sha256")
    if path is None or not path.is_file(): raise RuntimeError("Phase 381 candidate dataset is missing.")
    row_count=0; previous=-1; duplicate_or_unsorted=0; provider_count_failures=0; schema_failures=0; empty_consensus=0
    for row in stream_candidate_rows(path):
        row_count+=1
        if tuple(row.keys())!=CANDIDATE_SCHEMA: schema_failures+=1
        ts=int(row["open_time_ms"])
        if ts<=previous: duplicate_or_unsorted+=1
        previous=ts
        if int(row["provider_count"])<3: provider_count_failures+=1
        if not row["consensus_close"].strip(): empty_consensus+=1
    expected_rows=int(p367.get("metrics",{}).get("VALID_CONSENSUS_HOURS",-1))
    checks={"candidate_hash_matches":sha256_file(path)==expected,"row_count_positive":row_count>0,"row_count_matches_phase367":row_count==expected_rows,"schema_failures_zero":schema_failures==0,"timestamps_strictly_increasing":duplicate_or_unsorted==0,"minimum_provider_failures_zero":provider_count_failures==0,"empty_consensus_zero":empty_consensus==0,"dry_run_pass":p380.get("dry_run_pass") is True}
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 381 integrity audit failed; failed_checks={failed!r}.")
    payload=base_payload(381,"NONCANONICAL_RESEARCH_DATASET_INTEGRITY_AUDIT_PASS_RESEARCH_ONLY"); payload.update({"gate":"PHASE381_NONCANONICAL_RESEARCH_DATASET_INTEGRITY_AUDIT_READY_RESEARCH_ONLY","integrity_checks":checks,"failed_checks":[],"integrity_pass":True,"candidate_row_count":row_count,"candidate_sha256":expected,"schema_failure_count":schema_failures,"duplicate_or_unsorted_timestamp_count":duplicate_or_unsorted,"minimum_provider_failure_count":provider_count_failures,"empty_consensus_count":empty_consensus,"canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase381_noncanonical_research_dataset_integrity_audit.json",payload)
    write_summary(phase_summary(381,"noncanonical_research_dataset_integrity_audit"),title="Phase 381 — Noncanonical Research-dataset Integrity Audit",gate=payload["gate"],bullets=["Integrity pass: `True`",f"Candidate rows: `{row_count}`","Schema failures: `0`","Timestamp order failures: `0`","Canonical writes: `0`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase367-artifact",type=Path,default=art/"phase367_one_real_data_remediation_evaluation_research_only/phase367_one_real_data_remediation_evaluation.json"); a.add_argument("--phase379-artifact",type=Path,default=art/"phase379_noncanonical_research_dataset_schema_and_lineage_contract_research_only/phase379_noncanonical_research_dataset_schema_and_lineage_contract.json"); a.add_argument("--phase380-artifact",type=Path,default=art/"phase380_synthetic_noncanonical_adoption_dry_run_research_only/phase380_synthetic_noncanonical_adoption_dry_run.json"); a.add_argument("--output-dir",type=Path,default=art/"phase381_noncanonical_research_dataset_integrity_audit_research_only"); x=a.parse_args(); p=build(x.phase367_artifact,x.phase379_artifact,x.phase380_artifact,x.output_dir); print(p["gate"]); print("Integrity pass:",p["integrity_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
