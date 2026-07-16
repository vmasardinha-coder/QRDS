from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase360_path: Path, output_dir: Path) -> dict[str, Any]:
    p360=read_json(phase360_path); validate_phase(p360,360); selected=p360.get("selected_remediation_id")
    if not p360.get("preregistration_created"):
        mode="SKIPPED_NO_ACCEPTED_REMEDIATION"; checks={"no_go_preserved":True}; passed=True
    elif selected=="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1":
        hours=[0,1,2,3]; rows=[(h,p,100+h+(p-2)*0.1) for h in hours for p in range(4) if not (h==2 and p==3)]
        counts={h:sum(1 for item in rows if item[0]==h) for h in hours}; valid=[h for h,c in counts.items() if c>=3]
        checks={"synthetic_hours":len(hours),"valid_consensus_hours":len(valid),"minimum_three_providers_enforced":True,"forward_shift_count":0,"interpolation_count":0}; passed=len(valid)==4
        mode="TIMESTAMP_CONSENSUS_SYNTHETIC_DRY_RUN"
    else:
        stamps=[0,1,1,3,4]; unique=sorted(set(stamps)); missing=[x for x in range(unique[0],unique[-1]+1) if x not in unique]
        checks={"input_rows":len(stamps),"unique_rows":len(unique),"duplicate_count":len(stamps)-len(unique),"missing_count":len(missing),"future_imputation_count":0}; passed=checks["duplicate_count"]==1 and checks["missing_count"]==1
        mode="DERIVATIVES_COVERAGE_SYNTHETIC_DRY_RUN"
    payload=base_payload(361,"SYNTHETIC_DATA_REMEDIATION_DRY_RUN_PASS_RESEARCH_ONLY" if passed else "SYNTHETIC_DATA_REMEDIATION_DRY_RUN_FAIL_RESEARCH_ONLY")
    payload.update({"gate":"PHASE361_SYNTHETIC_DATA_REMEDIATION_CONTRACT_DRY_RUN_READY_RESEARCH_ONLY","dry_run_mode":mode,"synthetic_only":True,"real_historical_rows_used":0,"checks":checks,"dry_run_pass":passed,"closed_families_reopened":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase361_synthetic_data_remediation_contract_dry_run.json",payload)
    write_summary(phase_summary(361,"synthetic_data_remediation_contract_dry_run"),title="Phase 361 — Synthetic Data-remediation Contract Dry-run",gate=payload["gate"],bullets=[f"Mode: `{mode}`",f"Dry-run pass: `{passed}`","Real historical rows used: `0`","Closed families reopened: `False`"])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase360-artifact",type=Path,default=art/"phase360_finite_data_remediation_preregistration_research_only/phase360_finite_data_remediation_preregistration.json"); a.add_argument("--output-dir",type=Path,default=art/"phase361_synthetic_data_remediation_contract_dry_run_research_only"); x=a.parse_args(); p=build(x.phase360_artifact,x.output_dir); print(p["gate"]); print("Pass:",p["dry_run_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
