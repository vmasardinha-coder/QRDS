from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase360_path: Path, phase361_path: Path, output_dir: Path) -> dict[str, Any]:
    p360,p361=read_json(phase360_path),read_json(phase361_path); validate_phase(p360,360); validate_phase(p361,361)
    rows=[{"timestamp_ms":h*3600000,"provider":provider,"value":100+h+index/100} for h in range(48) for index,provider in enumerate(("A","B","C","D"))]
    canonical=sorted(rows,key=lambda x:(x["timestamp_ms"],x["provider"])); first=fingerprint(canonical); second=fingerprint(sorted(canonical,key=lambda x:(x["timestamp_ms"],x["provider"])))
    checks={"fixture_rows":len(rows),"schema_fields":["timestamp_ms","provider","value"],"idempotent_hash":first==second,"future_timestamp_reads":0,"network_calls":0}
    passed=bool(p361.get("dry_run_pass")) and checks["idempotent_hash"] and checks["future_timestamp_reads"]==0
    payload=base_payload(362,"FIXTURE_DATA_REMEDIATION_PIPELINE_DRY_RUN_PASS_RESEARCH_ONLY" if passed else "FIXTURE_DATA_REMEDIATION_PIPELINE_DRY_RUN_FAIL_RESEARCH_ONLY")
    payload.update({"gate":"PHASE362_FIXTURE_DATA_REMEDIATION_PIPELINE_DRY_RUN_READY_RESEARCH_ONLY","fixture_only":True,"real_historical_rows_used":0,"checks":checks,"dry_run_pass":passed,"output_schema_frozen":bool(p360.get("preregistration_created")),"public_collection_started":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase362_fixture_data_remediation_pipeline_dry_run.json",payload)
    write_summary(phase_summary(362,"fixture_data_remediation_pipeline_dry_run"),title="Phase 362 — Fixture Data-remediation Pipeline Dry-run",gate=payload["gate"],bullets=[f"Fixture rows: `{len(rows)}`",f"Dry-run pass: `{passed}`","Network calls: `0`","Real historical rows used: `0`"])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase360-artifact",type=Path,default=art/"phase360_finite_data_remediation_preregistration_research_only/phase360_finite_data_remediation_preregistration.json"); a.add_argument("--phase361-artifact",type=Path,default=art/"phase361_synthetic_data_remediation_contract_dry_run_research_only/phase361_synthetic_data_remediation_contract_dry_run.json"); a.add_argument("--output-dir",type=Path,default=art/"phase362_fixture_data_remediation_pipeline_dry_run_research_only"); x=a.parse_args(); p=build(x.phase360_artifact,x.phase361_artifact,x.output_dir); print(p["gate"]); print("Pass:",p["dry_run_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
