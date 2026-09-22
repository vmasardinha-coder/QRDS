#!/usr/bin/env python3
"""Item 3D versioned historical economic survivor-candidate triage.

Uses only existing pre-D0 Item 3 evidence. The candidate tag is descriptive:
all 580 remain prospective-active, with zero survivor/promotion/trading credit.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from typing import Any

HARD_REASONS={"CONCENTRATION","DELAYED_ENTRY","REFERENCE_COST_EDGE","SIDE_STABILITY","STRESS_COST"}
CANDIDATE="HISTORICAL_SURVIVOR_CANDIDATE_FACILITATED"
WATCH="HISTORICAL_WATCH"
SOFT_SUPPORT_REASON="CALENDAR_HALF_STABILITY"

def load(p:Path)->Any: return json.loads(p.read_text(encoding="utf-8"))
def fid(r):
    for k in ("family_id","id","family"):
        if k in r:return str(r[k])
    raise KeyError("family id missing")
def rows(rt):
    v=rt.get("autonomous_base",{}).get("families")
    if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
    for k in ("families","family_results","results","reclassification_results"):
        v=rt.get(k)
        if isinstance(v,list): return [x for x in v if isinstance(x,dict)]
    return []
def cells(r):
    v=r.get("cells") or r.get("horizon_cells")
    return [x for x in v if isinstance(x,dict)] if isinstance(v,list) else []
def reasons_cell(c):
    v=c.get("reasons")
    if isinstance(v,list): return [str(x) for x in v]
    return [str(v)] if isinstance(v,str) else []
def all_reasons(r): return sorted({x for c in cells(r) for x in reasons_cell(c)})
def support_cells(r):
    out=[]
    for c in cells(r):
        rs=set(reasons_cell(c))
        if c.get("class")=="SOFT_INSUFFICIENT" and rs=={SOFT_SUPPORT_REASON}: out.append(c)
    return out
def minm(cs,k):
    v=[float(c[k]) for c in cs if isinstance(c.get(k),(int,float))]
    return min(v) if v else None
def summ(cs,k):
    v=[float(c[k]) for c in cs if isinstance(c.get(k),(int,float))]
    return sum(v) if v else None

def classify(rt):
    base=rt.get("autonomous_base",{})
    ids=base.get("experimental_shadow_eligible_ids") or rt.get("experimental_shadow_eligible_ids")
    if not isinstance(ids,list): raise ValueError("experimental_shadow_eligible_ids missing")
    elig={str(x) for x in ids}
    if len(elig)!=580: raise ValueError(f"expected 580 eligible families, got {len(elig)}")
    src={fid(r):r for r in rows(rt)}
    out=[]; missing=0
    for f in sorted(elig):
        r=src.get(f,{})
        if not r: missing+=1
        rs=all_reasons(r); hard=sorted(HARD_REASONS.intersection(rs)); sc=support_cells(r)
        label=CANDIDATE if not hard and len(sc)>=2 else WATCH
        out.append({
          "family_id":f,"label":label,"feature":r.get("feature"),"direction":r.get("direction"),
          "decision_window_minutes":r.get("decision_window_minutes"),"abs_z_threshold":r.get("abs_z_threshold"),
          "standardization_lookback_sessions":r.get("standardization_lookback_sessions"),"evidence_basis":r.get("evidence_basis"),
          "candidate_support_cell_count":len(sc),"candidate_support_horizons":[c.get("horizon") for c in sc],
          "hard_reasons":hard,"all_reasons":rs,
          "reference_cost_edge":minm(sc,"net2"),"stress_cost_edge":minm(sc,"net3"),
          "delayed_entry_edge":minm(sc,"delayed_net2"),"trade_count":summ(sc,"trades"),
          "cells":[{"horizon":c.get("horizon"),"class":c.get("class"),"reasons":reasons_cell(c),
                    "trades":c.get("trades"),"net2":c.get("net2"),"net3":c.get("net3"),"delayed_net2":c.get("delayed_net2")}
                   for c in cells(r)],
          "historical_detail_available":bool(r),"prospective_survivor_credit":0,"promotion_authority":False
        })
    def nk(v): return (1,0.0) if v is None else (0,-v)
    out.sort(key=lambda x:(0 if x["label"]==CANDIDATE else 1,-x["candidate_support_cell_count"],nk(x["reference_cost_edge"]),nk(x["stress_cost_edge"]),nk(x["delayed_entry_edge"]),nk(x["trade_count"]),x["family_id"]))
    for i,r in enumerate(out,1):r["rank"]=i
    counts={}
    for r in out: counts[r["label"]]=counts.get(r["label"],0)+1
    cand=[r for r in out if r["label"]==CANDIDATE]
    return {"schema":"gate_btc_2.factory_item3d_historical_survivor_triage.v3",
      "status":"HISTORICAL_TRIAGE_COMPLETE" if missing==0 else "HISTORICAL_TRIAGE_PARTIAL_SOURCE_DETAIL",
      "methodology":"VERSIONED_USER_DIRECTED_HISTORICAL_ECONOMIC_SCREEN",
      "population_count":580,"historical_survivor_candidate_count":len(cand),"family_state_counts":counts,
      "missing_historical_detail_count":missing,"top_candidate_ids":[r["family_id"] for r in cand[:50]],"families":out,
      "all_580_remain_forward_active":True,"prospective_survivor_credit":0,"survivor_promotion_authority":False,
      "engine_feed":False,"orders":0,"real_capital":0,"no_retune":True,"no_backfill":True,"h1_h31_runtime_mutation":False}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--runtime",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    r=classify(load(Path(a.runtime))); Path(a.out).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    cand=[x for x in r["families"] if x["label"]==CANDIDATE]
    print(json.dumps({"status":r["status"],"methodology":r["methodology"],"population":580,"candidate_count":len(cand),
      "counts":r["family_state_counts"],"missing_detail":r["missing_historical_detail_count"],
      "candidates":[{"id":x["family_id"],"support":x["candidate_support_cell_count"],"net2":x["reference_cost_edge"],"net3":x["stress_cost_edge"],"delayed":x["delayed_entry_edge"],"trades":x["trade_count"]} for x in cand]},sort_keys=True))
if __name__=="__main__": main()
