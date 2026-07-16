from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import ROOT, base_payload, fingerprint, read_json, validate_phase, write_json, write_summary


def build(phase301_path: Path, output_dir: Path) -> dict[str,Any]:
    p301=read_json(phase301_path); validate_phase(p301,301)
    audits=[]
    for name,record in sorted(p301.get("datasets",{}).items()):
        quality=record.get("quality",{}) if isinstance(record,dict) else {}
        rows=int(record.get("rows",0)); missing=int(quality.get("missing_interval_count",0)); duplicates=int(quality.get("duplicate_count",0)); expected=rows+missing; ratio=(rows/expected if expected else 0.0)
        audits.append({"dataset":name,"rows":rows,"start_ms":record.get("start_ms"),"end_ms":record.get("end_ms"),"missing_interval_count":missing,"duplicate_count":duplicates,"coverage_ratio":ratio,"sha256":record.get("sha256")})
    candle=[x for x in audits if x["dataset"].endswith("_candles")]
    derivatives=[x for x in audits if not x["dataset"].endswith("_candles")]
    min_candle=min((x["coverage_ratio"] for x in candle),default=0.0); good_candles=sum(x["rows"]>=720 and x["coverage_ratio"]>=0.98 for x in candle)
    coverage_pass=len(candle)>=2 and good_candles>=2
    payload=base_payload(319,"DATA_COVERAGE_AUDITED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE319_DATA_COVERAGE_AUDIT_V2_READY_RESEARCH_ONLY","dataset_count":len(audits),"candle_dataset_count":len(candle),"derivatives_dataset_count":len(derivatives),"dataset_audits":audits,"minimum_candle_coverage_ratio":min_candle,"candle_datasets_meeting_threshold":good_candles,"coverage_threshold":0.98,"coverage_audit_pass":coverage_pass,"new_strategy_budget_created":False,"strategy_approved":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase319_data_coverage_audit_v2.json",payload)
    write_summary(ROOT/"docs/reports/data_quality_v2/phase319_data_coverage_audit_v2_summary.md",title="Phase 319 — Data Coverage Audit v2",gate=payload["gate"],bullets=[f"Datasets audited: `{len(audits)}`",f"Candle datasets: `{len(candle)}`",f"Candle datasets above 98% coverage: `{good_candles}`",f"Coverage audit pass: `{coverage_pass}`","No strategy budget was created."])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase301-artifact",type=Path,default=art/"phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json"); a.add_argument("--output-dir",type=Path,default=art/"phase319_data_coverage_audit_v2_research_only"); x=a.parse_args(); p=build(x.phase301_artifact,x.output_dir); print(p["gate"]); print("Datasets:",p["dataset_count"]); print("Coverage audit pass:",p["coverage_audit_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
