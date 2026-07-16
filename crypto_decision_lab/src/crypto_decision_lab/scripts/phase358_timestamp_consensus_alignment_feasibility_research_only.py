from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase301_path: Path, phase320_path: Path, phase356_path: Path, output_dir: Path) -> dict[str, Any]:
    p301,p320,p356=read_json(phase301_path),read_json(phase320_path),read_json(phase356_path)
    validate_phase(p301,301); validate_phase(p320,320); validate_phase(p356,356)
    providers=int(p320.get("provider_dataset_count",0)); common=int(p320.get("common_hour_count",0)); spread=float(p320.get("spread_bps_p95",0.0))
    feasible=providers>=3 and common>=720
    clauses=[
        "USE_ONLY_CLOSED_HOURLY_CANDLES",
        "EXACT_UTC_HOUR_BUCKET_NO_FORWARD_SHIFT",
        "MINIMUM_THREE_PROVIDERS_FOR_CONSENSUS",
        "MEDIAN_PRICE_CONSENSUS",
        "NO_INTERPOLATION_ACROSS_MISSING_HOURS",
        "DERIVATIVES_CONTEXT_ASOF_PRIOR_TIMESTAMP_ONLY",
        "RECORD_PROVIDER_COUNT_AND_DISAGREEMENT_PER_HOUR",
    ]
    payload=base_payload(358,"TIMESTAMP_CONSENSUS_ALIGNMENT_FEASIBILITY_AUDITED_RESEARCH_ONLY")
    payload.update({
        "gate":"PHASE358_TIMESTAMP_CONSENSUS_ALIGNMENT_FEASIBILITY_READY_RESEARCH_ONLY",
        "provider_dataset_count":providers,"common_hour_count":common,"baseline_spread_p95_bps":spread,
        "alignment_contract_clauses":clauses,"alignment_contract_clause_count":len(clauses),
        "material_improvement_feasible_with_existing_data":feasible,
        "requires_new_public_collection":False,"future_leakage_allowed":False,"closed_families_reopened":False,
        "recommendation":"PREFERRED_ONE_FINITE_REMEDIATION_PREREGISTRATION" if feasible else "NO_GO_TIMESTAMP_CONSENSUS_REMEDIATION",
    })
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase358_timestamp_consensus_alignment_feasibility.json",payload)
    write_summary(phase_summary(358,"timestamp_consensus_alignment_feasibility"),title="Phase 358 — Timestamp and Consensus Alignment Feasibility",gate=payload["gate"],bullets=[
        f"Providers: `{providers}`",f"Common hours: `{common}`",f"Baseline spread p95: `{spread:.2f} bps`",f"Feasible with existing data: `{feasible}`","Future leakage allowed: `False`",
    ])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    a.add_argument("--phase301-artifact",type=Path,default=art/"phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json")
    a.add_argument("--phase320-artifact",type=Path,default=art/"phase320_exchange_disagreement_audit_research_only/phase320_exchange_disagreement_audit.json")
    a.add_argument("--phase356-artifact",type=Path,default=art/"phase356_manual_data_remediation_backlog_freeze_research_only/phase356_manual_data_remediation_backlog_freeze.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase358_timestamp_consensus_alignment_feasibility_research_only")
    x=a.parse_args(); p=build(x.phase301_artifact,x.phase320_artifact,x.phase356_artifact,x.output_dir); print(p["gate"]); print("Feasible:",p["material_improvement_feasible_with_existing_data"]); return 0
if __name__=="__main__": raise SystemExit(main())
