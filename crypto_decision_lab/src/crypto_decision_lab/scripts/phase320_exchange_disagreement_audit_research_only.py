from __future__ import annotations
import argparse, statistics
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import ROOT, base_payload, dataset_path, finite_float, fingerprint, quantile, read_csv_gz_rows, read_json, validate_phase, write_json, write_summary


def build(phase301_path: Path, phase319_path: Path, output_dir: Path) -> dict[str,Any]:
    p301,p319=read_json(phase301_path),read_json(phase319_path); validate_phase(p301,301); validate_phase(p319,319)
    series={}
    for name in sorted(p301.get("datasets",{})):
        if not name.endswith("_candles"): continue
        rows=read_csv_gz_rows(dataset_path(p301,name)); values={}
        for row in rows:
            try: ts=int(row["open_time_ms"])
            except (KeyError,TypeError,ValueError): continue
            close=finite_float(row.get("close"))
            if close and close>0: values[ts]=close
        if values: series[name]=values
    if len(series)<2: overlap=set()
    else: overlap=set.intersection(*(set(v) for v in series.values()))
    spreads=[]
    for ts in sorted(overlap):
        prices=[series[name][ts] for name in sorted(series)]; median=statistics.median(prices)
        if median>0: spreads.append((max(prices)-min(prices))/median*10000.0)
    p50=quantile(spreads,0.50); p95=quantile(spreads,0.95); p99=quantile(spreads,0.99); share25=(sum(v>25 for v in spreads)/len(spreads) if spreads else 0.0)
    available=len(series)>=2 and len(overlap)>=720
    payload=base_payload(320,"EXCHANGE_DISAGREEMENT_AUDITED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE320_EXCHANGE_DISAGREEMENT_AUDIT_READY_RESEARCH_ONLY","provider_dataset_count":len(series),"provider_datasets":sorted(series),"common_hour_count":len(overlap),"spread_bps_p50":p50,"spread_bps_p95":p95,"spread_bps_p99":p99,"share_hours_above_25bps":share25,"disagreement_context_available":available,"directional_signal_created":False,"new_strategy_budget_created":False,"strategy_approved":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase320_exchange_disagreement_audit.json",payload)
    write_summary(ROOT/"docs/reports/data_quality_v2/phase320_exchange_disagreement_audit_summary.md",title="Phase 320 — Exchange Disagreement Audit",gate=payload["gate"],bullets=[f"Providers compared: `{len(series)}`",f"Common hourly observations: `{len(overlap)}`",f"Median spread: `{p50:.2f} bps`",f"95th percentile spread: `{p95:.2f} bps`",f"Disagreement context available: `{available}`","No directional signal was created."])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase301-artifact",type=Path,default=art/"phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json"); a.add_argument("--phase319-artifact",type=Path,default=art/"phase319_data_coverage_audit_v2_research_only/phase319_data_coverage_audit_v2.json"); a.add_argument("--output-dir",type=Path,default=art/"phase320_exchange_disagreement_audit_research_only"); x=a.parse_args(); p=build(x.phase301_artifact,x.phase319_artifact,x.output_dir); print(p["gate"]); print("Common hours:",p["common_hour_count"]); print("Disagreement context available:",p["disagreement_context_available"]); return 0
if __name__=="__main__": raise SystemExit(main())
