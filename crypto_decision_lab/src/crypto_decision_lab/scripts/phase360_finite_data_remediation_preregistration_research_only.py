from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase357_path: Path, phase358_path: Path, phase359_path: Path, output_dir: Path) -> dict[str, Any]:
    p357,p358,p359=read_json(phase357_path),read_json(phase358_path),read_json(phase359_path)
    validate_phase(p357,357); validate_phase(p358,358); validate_phase(p359,359)
    selected=p359.get("selected_remediation_id"); accepted=bool(p359.get("remediation_accepted_for_preregistration"))
    if selected=="TIMESTAMP_CONSENSUS_ALIGNMENT_REMEDIATION_V1":
        metrics=["VALID_CONSENSUS_HOUR_RATIO","TIMESTAMP_MISMATCH_COUNT","PROVIDER_COUNT_DISTRIBUTION","CONSENSUS_SPREAD_P95_BPS"]
        criteria={"minimum_provider_count":3,"no_forward_shift":True,"no_interpolation":True,"valid_hour_ratio_not_lower_than_baseline":True,"timestamp_mismatch_count_must_decrease":True}
        network_needed=False
    elif selected=="PUBLIC_DERIVATIVES_COVERAGE_REMEDIATION_V1":
        metrics=["USABLE_FUNDING_DATASET_COUNT","USABLE_OPEN_INTEREST_DATASET_COUNT","MISSING_RATIO_BY_DATASET","DUPLICATE_TIMESTAMP_COUNT"]
        criteria={"no_private_api":True,"usable_dataset_count_must_increase_or_missingness_decrease":True,"relative_missingness_improvement_minimum":0.20,"no_imputation_from_future":True}
        network_needed=True
    else:
        metrics=[]; criteria={}; network_needed=False
    payload=base_payload(360,"FINITE_DATA_REMEDIATION_PREREGISTRATION_READY_RESEARCH_ONLY" if accepted else "DATA_REMEDIATION_NO_GO_PRESERVED_RESEARCH_ONLY")
    payload.update({
        "gate":"PHASE360_FINITE_DATA_REMEDIATION_PREREGISTRATION_READY_RESEARCH_ONLY",
        "selected_remediation_id":selected,"preregistration_created":accepted,"future_experiment_budget":1 if accepted else 0,
        "active_experiment_budget":0,"primary_metrics":metrics,"success_criteria":criteria,
        "strategy_or_return_metric_allowed":False,"closed_family_metric_reuse_allowed":False,
        "future_public_network_action_may_be_required":network_needed,"public_collection_started":False,
        "historical_remediation_evaluation_started":False,"stop_rule":"ONE_EVALUATION_THEN_CLOSE_OR_MANUAL_REVIEW" if accepted else "NO_EVALUATION",
    })
    payload["preregistration_fingerprint"]=fingerprint({k:v for k,v in payload.items() if k not in {"generated_at_utc","artifact_fingerprint"}})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase360_finite_data_remediation_preregistration.json",payload)
    write_summary(phase_summary(360,"finite_data_remediation_preregistration"),title="Phase 360 — Finite Data-remediation Preregistration",gate=payload["gate"],bullets=[
        f"Preregistration created: `{accepted}`",f"Future experiment budget: `{payload['future_experiment_budget']}`",f"Active experiment budget: `0`",f"Public collection started: `False`","Strategy metrics allowed: `False`",
    ])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    a.add_argument("--phase357-artifact",type=Path,default=art/"phase357_public_derivatives_coverage_feasibility_research_only/phase357_public_derivatives_coverage_feasibility.json")
    a.add_argument("--phase358-artifact",type=Path,default=art/"phase358_timestamp_consensus_alignment_feasibility_research_only/phase358_timestamp_consensus_alignment_feasibility.json")
    a.add_argument("--phase359-artifact",type=Path,default=art/"phase359_manual_data_remediation_decision_research_only/phase359_manual_data_remediation_decision.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase360_finite_data_remediation_preregistration_research_only")
    x=a.parse_args(); p=build(x.phase357_artifact,x.phase358_artifact,x.phase359_artifact,x.output_dir); print(p["gate"]); print("Preregistration created:",p["preregistration_created"]); return 0
if __name__=="__main__": raise SystemExit(main())
