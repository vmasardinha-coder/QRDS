from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import ROOT, base_payload, dataset_path, median_interval_ms, fingerprint, read_csv_gz_rows, read_json, validate_phase, write_json, write_summary


def _timestamp_key(name:str)->str:
    if "funding" in name: return "funding_time_ms"
    if "open_interest" in name: return "timestamp_ms"
    return "open_time_ms"

def build(phase301_path: Path, output_dir: Path) -> dict[str,Any]:
    p301=read_json(phase301_path); validate_phase(p301,301); audits=[]
    for name in sorted(p301.get("datasets",{})):
        if name.endswith("_candles"): continue
        rows=read_csv_gz_rows(dataset_path(p301,name)); key=_timestamp_key(name); stamps=[]
        for row in rows:
            try: stamps.append(int(row[key]))
            except (KeyError,TypeError,ValueError): pass
        unique=sorted(set(stamps)); interval=median_interval_ms(unique); expected=(int((unique[-1]-unique[0])//interval)+1 if interval and unique else len(unique)); missing=max(0,expected-len(unique)); missing_ratio=(missing/expected if expected else 1.0)
        audits.append({"dataset":name,"rows":len(unique),"inferred_interval_ms":interval,"expected_rows":expected,"missing_rows":missing,"missing_ratio":missing_ratio,"usable":len(unique)>=90 and missing_ratio<=0.25})
    funding=[x for x in audits if "funding" in x["dataset"]]; oi=[x for x in audits if "open_interest" in x["dataset"]]
    usable_funding=sum(x["usable"] for x in funding); usable_oi=sum(x["usable"] for x in oi); usable=usable_funding>=1 and usable_oi>=1
    payload=base_payload(321,"DERIVATIVES_MISSINGNESS_AUDITED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE321_DERIVATIVES_MISSINGNESS_AUDIT_READY_RESEARCH_ONLY","derivatives_dataset_count":len(audits),"dataset_audits":audits,"usable_funding_dataset_count":usable_funding,"usable_open_interest_dataset_count":usable_oi,"maximum_missing_ratio":0.25,"derivatives_context_usable":usable,"missingness_used_as_directional_signal":False,"new_strategy_budget_created":False,"strategy_approved":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase321_derivatives_missingness_audit.json",payload)
    write_summary(ROOT/"docs/reports/data_quality_v2/phase321_derivatives_missingness_audit_summary.md",title="Phase 321 — Derivatives Missingness Audit",gate=payload["gate"],bullets=[f"Derivatives datasets audited: `{len(audits)}`",f"Usable funding datasets: `{usable_funding}`",f"Usable open-interest datasets: `{usable_oi}`",f"Derivatives context usable: `{usable}`","Missingness was not converted into a directional signal."])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase301-artifact",type=Path,default=art/"phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json"); a.add_argument("--output-dir",type=Path,default=art/"phase321_derivatives_missingness_audit_research_only"); x=a.parse_args(); p=build(x.phase301_artifact,x.output_dir); print(p["gate"]); print("Derivatives context usable:",p["derivatives_context_usable"]); return 0
if __name__=="__main__": raise SystemExit(main())
