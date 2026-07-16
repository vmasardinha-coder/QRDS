from __future__ import annotations
import argparse
from collections import Counter
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import ROOT, base_payload, fingerprint, read_json, validate_phase, write_json, write_summary

CATEGORY_MAP={
 "PHASE304_SELECTION_NOT_STABLE":"SELECTION_INSTABILITY","MODAL_SHARE_BELOW_70_PERCENT":"SELECTION_INSTABILITY","EARLY_AND_LATE_WINDOWS_DISAGREE":"SELECTION_INSTABILITY","TOO_MANY_SELECTION_TRANSITIONS":"SELECTION_INSTABILITY","NO_LONG_CONTIGUOUS_MODAL_RUN":"SELECTION_INSTABILITY",
 "REGIME_CONCENTRATION":"REGIME_DEPENDENCE","HYPOTHESIS_DEPENDENCE":"SEARCH_SPACE_REDUNDANCY","EXTREME_COST_LIQUIDITY":"COST_LIQUIDITY_FRAGILITY","TIMESTAMP_SENSITIVITY":"TIMING_FRAGILITY",
}

def build(paths: list[Path], phase316_path: Path, output_dir: Path) -> dict[str,Any]:
    p316=read_json(phase316_path); validate_phase(p316,316)
    failures=[]
    for phase,path in zip(range(306,312),paths):
        item=read_json(path); validate_phase(item,phase)
        reasons=list(item.get("failure_reasons",[]))
        if phase==307 and not item.get("regime_concentration_pass",False): reasons.append("REGIME_CONCENTRATION")
        if phase==308 and not item.get("dependency_pass",False): reasons.append("HYPOTHESIS_DEPENDENCE")
        if phase==309 and not item.get("extreme_cost_liquidity_pass",False): reasons.append("EXTREME_COST_LIQUIDITY")
        if phase==310 and not item.get("timestamp_sensitivity_pass",False): reasons.append("TIMESTAMP_SENSITIVITY")
        for reason in reasons: failures.append({"phase":phase,"reason":reason,"category":CATEGORY_MAP.get(reason,"ELIGIBILITY_GATE_FAILURE")})
    for gate_id in p316.get("failed_gate_ids",[]): failures.append({"phase":311,"reason":gate_id,"category":"ELIGIBILITY_GATE_FAILURE"})
    counts=Counter(x["category"] for x in failures)
    payload=base_payload(318,"FAILURE_ATLAS_REGISTERED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE318_FAILURE_ATLAS_READY_RESEARCH_ONLY","closed_family_signature_sha256":p316["closed_family_signature_sha256"],"failure_record_count":len(failures),"failure_category_count":len(counts),"failure_category_counts":dict(sorted(counts.items())),"failure_records":failures,"silent_recycling_allowed":False,"strategy_approved":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase318_failure_atlas.json",payload)
    write_summary(ROOT/"docs/reports/negative_evidence/phase318_failure_atlas_summary.md",title="Phase 318 — Failure Atlas",gate=payload["gate"],bullets=[f"Failure records: `{len(failures)}`",f"Failure categories: `{len(counts)}`","Silent recycling: `False`","Interpretation: the family failed for documented reasons, not because the software failed."])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"
    defaults=[art/"phase306_temporal_selection_stability_audit_research_only/phase306_temporal_selection_stability_audit.json",art/"phase307_regime_concentration_audit_research_only/phase307_regime_concentration_audit.json",art/"phase308_hypothesis_dependence_audit_research_only/phase308_hypothesis_dependence_audit.json",art/"phase309_extreme_cost_liquidity_audit_research_only/phase309_extreme_cost_liquidity_audit.json",art/"phase310_timestamp_sensitivity_audit_research_only/phase310_timestamp_sensitivity_audit.json",art/"phase311_candidate_eligibility_contract_v2_research_only/phase311_candidate_eligibility_contract_v2.json"]
    for phase,d in zip(range(306,312),defaults): a.add_argument(f"--phase{phase}-artifact",type=Path,default=d)
    a.add_argument("--phase316-artifact",type=Path,default=art/"phase316_negative_evidence_registry_research_only/phase316_negative_evidence_registry.json"); a.add_argument("--output-dir",type=Path,default=art/"phase318_failure_atlas_research_only"); x=a.parse_args(); paths=[getattr(x,f"phase{p}_artifact") for p in range(306,312)]; p=build(paths,x.phase316_artifact,x.output_dir); print(p["gate"]); print("Failure records:",p["failure_record_count"]); print("Strategy approved:",p["strategy_approved"]); return 0
if __name__=="__main__": raise SystemExit(main())
