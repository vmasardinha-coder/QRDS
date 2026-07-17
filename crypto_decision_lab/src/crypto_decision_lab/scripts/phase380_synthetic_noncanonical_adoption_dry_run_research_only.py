from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import CANDIDATE_SCHEMA, ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary

def _synthetic_rows()->list[dict[str,Any]]:
    return [{"open_time_ms":0,"open_time_utc":"1970-01-01T00:00:00Z","provider_count":3,"providers":"A|B|C","consensus_close":"100.000000000000","spread_bps":"2.00000000"},{"open_time_ms":3600000,"open_time_utc":"1970-01-01T01:00:00Z","provider_count":4,"providers":"A|B|C|D","consensus_close":"101.000000000000","spread_bps":"1.00000000"}]

def build(phase379_path:Path,output_dir:Path)->dict[str,Any]:
    p379=read_json(phase379_path); validate_phase(p379,379); contract=p379.get("candidate_contract",{}); rows=_synthetic_rows()
    checks={"contract_frozen":p379.get("candidate_contract_frozen") is True,"schema_exact":tuple(contract.get("schema_fields",[]))==CANDIDATE_SCHEMA,"synthetic_only":True,"rows_match_schema":all(tuple(row.keys())==CANDIDATE_SCHEMA for row in rows),"minimum_provider_count_respected":all(int(row["provider_count"])>=3 for row in rows),"canonical_write_count_zero":contract.get("canonical_data_writes")==0}
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 380 dry-run failed; failed_checks={failed!r}.")
    payload=base_payload(380,"SYNTHETIC_NONCANONICAL_ADOPTION_DRY_RUN_PASS_RESEARCH_ONLY"); payload.update({"gate":"PHASE380_SYNTHETIC_NONCANONICAL_ADOPTION_DRY_RUN_READY_RESEARCH_ONLY","dry_run_checks":checks,"failed_checks":[],"dry_run_pass":True,"synthetic_rows_used":len(rows),"real_rows_used":0,"candidate_dataset_written":False,"canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase380_synthetic_noncanonical_adoption_dry_run.json",payload)
    write_summary(phase_summary(380,"synthetic_noncanonical_adoption_dry_run"),title="Phase 380 — Synthetic Noncanonical Adoption Dry-run",gate=payload["gate"],bullets=["Dry-run pass: `True`",f"Synthetic rows: `{len(rows)}`","Real rows used: `0`","Candidate dataset written: `False`","Canonical writes: `0`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase379-artifact",type=Path,default=art/"phase379_noncanonical_research_dataset_schema_and_lineage_contract_research_only/phase379_noncanonical_research_dataset_schema_and_lineage_contract.json"); a.add_argument("--output-dir",type=Path,default=art/"phase380_synthetic_noncanonical_adoption_dry_run_research_only"); x=a.parse_args(); p=build(x.phase379_artifact,x.output_dir); print(p["gate"]); print("Dry-run pass:",p["dry_run_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
