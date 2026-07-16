from __future__ import annotations
import argparse
from pathlib import Path
from typing import Any
from crypto_decision_lab.scripts.phase316_325_negative_evidence_common import PROPOSED_QUESTION_ID, ROOT, base_payload, fingerprint, prerequisite_record, read_json, validate_phase, write_json, write_summary

QUESTION="Can contemporaneous cross-exchange disagreement and derivatives-data quality identify periods when a directional research model should abstain, without predicting buy or sell direction?"

def build(paths: dict[int,Path], output_dir: Path) -> dict[str,Any]:
    p={phase:read_json(path) for phase,path in paths.items()}
    for phase,item in p.items(): validate_phase(item,phase)
    gates=[
      prerequisite_record("N01","Current directional family is formally closed",p[316].get("negative_result_registered") is True,p[316].get("current_family_decision"),"CURRENT_FAMILY_NOT_CLOSED"),
      prerequisite_record("N02","Exact and semantic retests are blocked",p[317].get("registry_closed") is True and p[317].get("prohibited_signature_count")==24,p[317].get("prohibited_signature_count"),"RETEST_SIGNATURE_REGISTRY_INCOMPLETE"),
      prerequisite_record("N03","Failure atlas is documented",p[318].get("failure_record_count",0)>0,p[318].get("failure_category_counts"),"FAILURE_ATLAS_EMPTY"),
      prerequisite_record("N04","Multi-source candle coverage is sufficient",p[319].get("coverage_audit_pass") is True,p[319].get("candle_datasets_meeting_threshold"),"DATA_COVERAGE_INSUFFICIENT"),
      prerequisite_record("N05","Cross-exchange disagreement is measurable",p[320].get("disagreement_context_available") is True,p[320].get("common_hour_count"),"DISAGREEMENT_CONTEXT_UNAVAILABLE"),
      prerequisite_record("N06","Derivatives data quality is measurable",p[321].get("derivatives_context_usable") is True,p[321].get("dataset_audits"),"DERIVATIVES_CONTEXT_UNUSABLE"),
      prerequisite_record("N07","Target is abstention/reliability, not directional return",True,"NON_DIRECTIONAL_ABSTENTION_TARGET","QUESTION_NOT_GENUINELY_DIFFERENT"),
      prerequisite_record("N08","No hypotheses or experiment budget are opened in this phase",True,{"hypotheses":0,"budget":0},"BUDGET_OPENED_PREMATURELY"),
    ]
    passed=sum(g["passed"] for g in gates); justified=passed==len(gates)
    payload=base_payload(322,"NEW_SCIENTIFIC_QUESTION_NOVELTY_AUDITED_RESEARCH_ONLY")
    payload.update({"gate":"PHASE322_NEW_SCIENTIFIC_QUESTION_NOVELTY_AUDIT_READY_RESEARCH_ONLY","proposed_question_id":PROPOSED_QUESTION_ID,"proposed_scientific_question":QUESTION,"target_type":"ABSTENTION_RELIABILITY_NOT_DIRECTIONAL_RETURN","question_output":"RESEARCH_ABSTAIN_OR_EVALUATE_ONLY","novelty_gate_count":len(gates),"passed_novelty_gate_count":passed,"failed_novelty_gate_count":len(gates)-passed,"failed_novelty_gate_ids":[g["gate_id"] for g in gates if not g["passed"]],"novelty_gates":gates,"genuinely_different_question_justified":justified,"hypotheses_registered":0,"experiment_budget_opened":False,"strategy_approved":False})
    payload["artifact_fingerprint"]=fingerprint(payload); output_dir.mkdir(parents=True,exist_ok=True); write_json(output_dir/"phase322_new_scientific_question_novelty_audit.json",payload)
    write_summary(ROOT/"docs/reports/new_family_preregistration/phase322_new_scientific_question_novelty_audit_summary.md",title="Phase 322 — New Scientific Question Novelty Audit",gate=payload["gate"],bullets=[f"Question ID: `{PROPOSED_QUESTION_ID}`",f"Passed novelty gates: `{passed}/{len(gates)}`",f"Genuinely different question justified: `{justified}`","Hypotheses registered: `0`","Experiment budget opened: `False`"])
    return payload

def main()->int:
    a=argparse.ArgumentParser(); art=ROOT/"artifacts"; defaults={316:art/"phase316_negative_evidence_registry_research_only/phase316_negative_evidence_registry.json",317:art/"phase317_prohibited_retest_signature_registry_research_only/phase317_prohibited_retest_signature_registry.json",318:art/"phase318_failure_atlas_research_only/phase318_failure_atlas.json",319:art/"phase319_data_coverage_audit_v2_research_only/phase319_data_coverage_audit_v2.json",320:art/"phase320_exchange_disagreement_audit_research_only/phase320_exchange_disagreement_audit.json",321:art/"phase321_derivatives_missingness_audit_research_only/phase321_derivatives_missingness_audit.json"}
    for phase,d in defaults.items(): a.add_argument(f"--phase{phase}-artifact",type=Path,default=d)
    a.add_argument("--output-dir",type=Path,default=art/"phase322_new_scientific_question_novelty_audit_research_only"); x=a.parse_args(); p=build({phase:getattr(x,f"phase{phase}_artifact") for phase in defaults},x.output_dir); print(p["gate"]); print("Question justified:",p["genuinely_different_question_justified"]); print("Experiment budget opened:",p["experiment_budget_opened"]); return 0
if __name__=="__main__": raise SystemExit(main())
