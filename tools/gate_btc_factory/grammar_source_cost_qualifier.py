#!/usr/bin/env python3
"""Fail-closed source/cost qualification for preregistered Grammar Scout families.

This executor evaluates evidence packets only. It never fetches market/outcome data and
never changes a grammar. Evidence must concern source availability/metadata and frozen
cost-contract identity only.
"""
import argparse, json
from pathlib import Path

def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))

def qualify(intake, protocol, evidence_dir):
    if not protocol.get("frozen_before_outcomes"): raise ValueError("FAIL_CLOSED: protocol not frozen")
    rows=[]
    for f in intake.get("families",[]):
        fid=f["family_id"]; ep=Path(evidence_dir)/(fid+".json")
        base={**f,"source_qualified":False,"cost_applicability_proven":False,"economics_read":False,"historical_testing_started":False}
        if not ep.exists():
            base.update(status="WAITING_SOURCE_COST_EVIDENCE",next_stage="SOURCE_COST_EVIDENCE_REQUIRED")
            rows.append(base); continue
        e=load(ep)
        if e.get("family_id")!=fid or e.get("grammar_signature")!=f.get("grammar_signature"):
            raise ValueError("FAIL_CLOSED: evidence identity mismatch "+fid)
        allowed=set(f.get("official_free_source_candidates",[])); chosen=e.get("qualified_sources",[])
        if not chosen or any(x not in allowed for x in chosen): raise ValueError("FAIL_CLOSED: non-preregistered source "+fid)
        checks=e.get("source_checks",{})
        required=["official_public_free","required_data_covered","pit_timestamps","granularity_sufficient","calendar_causal","reproducible_auditable"]
        source_ok=all(checks.get(k) is True for k in required)
        cost=e.get("cost_checks",{})
        cost_ok=cost.get("data_acquisition_zero") is True and cost.get("frozen_execution_cost_contract_preserved") is True and cost.get("no_new_economic_assumption") is True
        if e.get("outcomes_read") is not False or e.get("economics_read") is not False: raise ValueError("FAIL_CLOSED: premature outcome/economics read "+fid)
        if source_ok and cost_ok:
            base.update(status="SOURCE_COST_QUALIFIED",source_qualified=True,cost_applicability_proven=True,qualified_sources=sorted(chosen),next_stage="EXISTING_FACTORY_INTAKE")
        else:
            base.update(status="REJECT_SOURCE_COST_FAIL_CLOSED",next_stage="TERMINAL_SOURCE_COST_REJECTION")
        rows.append(base)
    return {"schema":"qrds.factory.grammar_source_cost_qualification_runtime.v1","protocol_schema":protocol["schema"],"families":rows,"qualified_count":sum(x["status"]=="SOURCE_COST_QUALIFIED" for x in rows),"waiting_count":sum(x["status"]=="WAITING_SOURCE_COST_EVIDENCE" for x in rows),"rejected_count":sum(x["status"]=="REJECT_SOURCE_COST_FAIL_CLOSED" for x in rows),"safety":protocol["safety"]}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--intake",required=True); ap.add_argument("--protocol",required=True); ap.add_argument("--evidence-dir",required=True); ap.add_argument("--output",required=True); a=ap.parse_args()
 out=qualify(load(a.intake),load(a.protocol),a.evidence_dir); Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps({k:out[k] for k in ("qualified_count","waiting_count","rejected_count")}))
if __name__=="__main__": main()
