from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase356_365_data_remediation_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary


def build(phase301_path: Path, phase321_path: Path, phase356_path: Path, output_dir: Path) -> dict[str, Any]:
    p301,p321,p356=read_json(phase301_path),read_json(phase321_path),read_json(phase356_path)
    validate_phase(p301,301); validate_phase(p321,321); validate_phase(p356,356)
    audits=list(p321.get("dataset_audits",[]))
    funding=[x for x in audits if "funding" in str(x.get("dataset",""))]
    oi=[x for x in audits if "open_interest" in str(x.get("dataset",""))]
    usable_funding=int(p321.get("usable_funding_dataset_count",0)); usable_oi=int(p321.get("usable_open_interest_dataset_count",0))
    provider_diversity_gap = usable_funding < 2 or usable_oi < 2
    missingness_gap = any(float(x.get("missing_ratio",0.0)) > 0.01 for x in audits)
    existing_specs_verified = bool(p301.get("official_endpoint_registry")) and bool(p301.get("official_docs_verified_on"))
    feasible = existing_specs_verified and (provider_diversity_gap or missingness_gap)
    payload=base_payload(357,"PUBLIC_DERIVATIVES_COVERAGE_FEASIBILITY_AUDITED_RESEARCH_ONLY")
    payload.update({
        "gate":"PHASE357_PUBLIC_DERIVATIVES_COVERAGE_FEASIBILITY_READY_RESEARCH_ONLY",
        "funding_dataset_count":len(funding),"open_interest_dataset_count":len(oi),
        "usable_funding_dataset_count":usable_funding,"usable_open_interest_dataset_count":usable_oi,
        "provider_diversity_gap":provider_diversity_gap,"missingness_gap":missingness_gap,
        "existing_public_endpoint_specs_verified":existing_specs_verified,
        "material_improvement_feasible_without_private_api":feasible,
        "allowed_future_method":"BOUNDED_RECOLLECTION_FROM_ALREADY_VERIFIED_PUBLIC_NO_AUTH_ROUTES_ONLY",
        "new_endpoint_claimed":False,"public_collection_started":False,"private_api_required":False,
        "closed_families_reopened":False,"recommendation":"ELIGIBLE_FOR_ONE_FINITE_REMEDIATION_PREREGISTRATION" if feasible else "NO_GO_CURRENT_PUBLIC_COVERAGE_REMEDIATION",
    })
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase357_public_derivatives_coverage_feasibility.json",payload)
    write_summary(phase_summary(357,"public_derivatives_coverage_feasibility"),title="Phase 357 — Public Derivatives Coverage Feasibility",gate=payload["gate"],bullets=[
        f"Usable funding datasets: `{usable_funding}`",f"Usable open-interest datasets: `{usable_oi}`",f"Provider diversity gap: `{provider_diversity_gap}`",f"Material improvement feasible: `{feasible}`","Public collection started: `False`",
    ])
    return payload


def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    a.add_argument("--phase301-artifact",type=Path,default=art/"phase301_official_public_history_extension_research_only/phase301_official_public_history_extension.json")
    a.add_argument("--phase321-artifact",type=Path,default=art/"phase321_derivatives_missingness_audit_research_only/phase321_derivatives_missingness_audit.json")
    a.add_argument("--phase356-artifact",type=Path,default=art/"phase356_manual_data_remediation_backlog_freeze_research_only/phase356_manual_data_remediation_backlog_freeze.json")
    a.add_argument("--output-dir",type=Path,default=art/"phase357_public_derivatives_coverage_feasibility_research_only")
    x=a.parse_args(); p=build(x.phase301_artifact,x.phase321_artifact,x.phase356_artifact,x.output_dir); print(p["gate"]); print("Feasible:",p["material_improvement_feasible_without_private_api"]); return 0
if __name__=="__main__": raise SystemExit(main())
