from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase376_385_remediated_dataset_adoption_common import ROOT, base_payload, fingerprint, phase_summary, read_json, validate_phase, write_json, write_summary

def build(phase369_path:Path,phase375_path:Path,phase377_path:Path,output_dir:Path)->dict[str,Any]:
    p369=read_json(phase369_path); p375=read_json(phase375_path); p377=read_json(phase377_path)
    for phase,p in ((369,p369),(375,p375),(377,p377)): validate_phase(p,phase)
    checks={"adoption_scope_noncanonical_only":p377.get("approved_scope")=="NONCANONICAL_RESEARCH_INPUT_METADATA_REGISTRY_ONLY","canonical_adoption_forbidden":p377.get("canonical_adoption_approved") is False,"strategy_use_forbidden":p377.get("strategy_use_approved") is False,"closed_family_retest_forbidden":p377.get("closed_family_retest_authorized") is False,"phase369_proof_pass":p369.get("proof_pass") is True,"closed_family_metric_unused":p375.get("no_closed_family_metric_proof_pass") is True,"closed_families_remain_closed":p375.get("closed_families_reopened") is False}
    failed=sorted(k for k,v in checks.items() if not v)
    if failed: raise RuntimeError(f"Phase 378 isolation checks failed; failed_checks={failed!r}.")
    payload=base_payload(378,"CLOSED_FAMILY_ISOLATION_AUDIT_PASS_RESEARCH_ONLY"); payload.update({"gate":"PHASE378_CLOSED_FAMILY_ISOLATION_AUDIT_READY_RESEARCH_ONLY","isolation_checks":checks,"failed_checks":[],"isolation_pass":True,"closed_families_reopened":False,"closed_family_artifact_read_count":0,"closed_family_performance_metric_read_count":0,"strategy_metric_authorized":False,"canonical_data_writes":0})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase378_closed_family_isolation_audit.json",payload)
    write_summary(phase_summary(378,"closed_family_isolation_audit"),title="Phase 378 — Closed-family Isolation Audit",gate=payload["gate"],bullets=["Isolation pass: `True`","Closed families reopened: `False`","Closed-family performance metrics read: `0`","Canonical data writes: `0`"]) ; return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; a.add_argument("--phase369-artifact",type=Path,default=art/"phase369_no_closed_family_performance_metric_proof_research_only/phase369_no_closed_family_performance_metric_proof.json"); a.add_argument("--phase375-artifact",type=Path,default=art/"phase375_data_quality_remediation_integrated_checkpoint_research_only/phase375_data_quality_remediation_integrated_checkpoint.json"); a.add_argument("--phase377-artifact",type=Path,default=art/"phase377_manual_noncanonical_research_input_adoption_review_research_only/phase377_manual_noncanonical_research_input_adoption_review.json"); a.add_argument("--output-dir",type=Path,default=art/"phase378_closed_family_isolation_audit_research_only"); x=a.parse_args(); p=build(x.phase369_artifact,x.phase375_artifact,x.phase377_artifact,x.output_dir); print(p["gate"]); print("Isolation pass:",p["isolation_pass"]); return 0
if __name__=="__main__": raise SystemExit(main())
