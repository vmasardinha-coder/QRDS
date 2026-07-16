from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import ROOT, base_payload, canonical_hash, fingerprint, hypothesis_signature, read_json, validate_phase, write_json, write_summary


def build(phase303_path: Path, phase316_path: Path, output_dir: Path) -> dict[str, Any]:
    p303,p316=read_json(phase303_path),read_json(phase316_path); validate_phase(p303,303); validate_phase(p316,316)
    signatures=[hypothesis_signature(item) for item in p303.get("hypotheses",[])]
    ids=[item["hypothesis_id"] for item in signatures]; hashes=[item["signature_sha256"] for item in signatures]
    if len(ids)!=24 or len(ids)!=len(set(ids)) or len(hashes)!=len(set(hashes)):
        raise RuntimeError("Prohibited signature registry is not one-to-one for the 24 hypotheses.")
    aliases=[]
    for item in signatures:
        fields=item["canonical_fields"]
        aliases.append({
            "hypothesis_id": item["hypothesis_id"],
            "signature_sha256": item["signature_sha256"],
            "semantic_key": canonical_hash({k:fields.get(k) for k in ("family","feature","lookback_hours","holding_hours","direction","filters")}),
            "prohibited_changes_that_do_not_create_novelty": ["rename_only","threshold_micro_tuning_after_result","holding_plus_or_minus_one_without_new_question","provider_alias_only","cost_assumption_relaxation"],
        })
    payload=base_payload(317,"PROHIBITED_RETEST_SIGNATURES_FROZEN_RESEARCH_ONLY")
    payload.update({
        "gate":"PHASE317_PROHIBITED_RETEST_SIGNATURE_REGISTRY_READY_RESEARCH_ONLY",
        "closed_family_signature_sha256":p316["closed_family_signature_sha256"],
        "prohibited_signature_count":len(signatures),
        "semantic_alias_count":len(aliases),
        "retest_policy":"BLOCK_EXACT_AND_SEMANTIC_ALIAS_RECYCLING",
        "automatic_waiver_allowed":False,
        "registry_closed":True,
        "new_experiment_budget":0,
        "strategy_approved":False,
    })
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True)
    write_json(output_dir/"phase317_prohibited_retest_signature_registry.json",payload)
    write_json(output_dir/"prohibited_retest_signatures.json",{"signatures":signatures,"semantic_aliases":aliases})
    write_summary(ROOT/"docs/reports/negative_evidence/phase317_prohibited_retest_signature_registry_summary.md",title="Phase 317 — Prohibited Retest Signatures",gate=payload["gate"],bullets=[f"Exact signatures blocked: `{len(signatures)}`",f"Semantic aliases tracked: `{len(aliases)}`","Automatic waiver: `False`","New experiment budget: `0`"])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase303-artifact",type=Path,default=art/"phase303_finite_hypothesis_registry_v2_research_only/phase303_finite_hypothesis_registry_v2.json"); a.add_argument("--phase316-artifact",type=Path,default=art/"phase316_negative_evidence_registry_research_only/phase316_negative_evidence_registry.json"); a.add_argument("--output-dir",type=Path,default=art/"phase317_prohibited_retest_signature_registry_research_only"); x=a.parse_args(); p=build(x.phase303_artifact,x.phase316_artifact,x.output_dir); print(p["gate"]); print("Blocked signatures:",p["prohibited_signature_count"]); print("New experiment budget:",p["new_experiment_budget"]); return 0
if __name__=="__main__": raise SystemExit(main())
