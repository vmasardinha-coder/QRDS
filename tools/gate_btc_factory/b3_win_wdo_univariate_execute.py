#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

FAMILIES = {
    "B3WIN01": ("WIN", "BODY_CONTINUATION"),
    "B3WIN02": ("WIN", "BODY_REVERSAL"),
    "B3WIN03": ("WIN", "CLOSE_LOCATION_CONTINUATION"),
    "B3WIN04": ("WIN", "CLOSE_LOCATION_REVERSAL"),
    "B3WIN05": ("WIN", "VOLUME_SHOCK_CONTINUATION"),
    "B3WIN06": ("WIN", "VOLUME_SHOCK_REVERSAL"),
    "B3WDO01": ("WDO", "BODY_CONTINUATION"),
    "B3WDO02": ("WDO", "BODY_REVERSAL"),
    "B3WDO03": ("WDO", "CLOSE_LOCATION_CONTINUATION"),
    "B3WDO04": ("WDO", "CLOSE_LOCATION_REVERSAL"),
    "B3WDO05": ("WDO", "VOLUME_SHOCK_CONTINUATION"),
    "B3WDO06": ("WDO", "VOLUME_SHOCK_REVERSAL"),
}
SAFETY = {"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True,"H1_ECONOMICS_READ":False}
POINT_VALUE = {"WIN": 0.20, "WDO": 10.0}
COST = {"WIN": 0.50, "WDO": 2.12}
KNOWN_GAP = "2021-06-10"


def mean(xs): return sum(xs)/len(xs) if xs else 0.0

def stdev(xs):
    if len(xs) < 2: return 0.0
    m=mean(xs); return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))

def sharpe(xs):
    s=stdev(xs); return (mean(xs)/s)*math.sqrt(252.0) if s>0 else 0.0

def compounded(xs):
    e=1.0
    for x in xs: e *= 1.0+x
    return e-1.0

def max_drawdown(xs):
    eq=1.0; peak=1.0; mdd=0.0
    for r in xs:
        eq *= 1.0+r; peak=max(peak,eq); mdd=max(mdd,(peak-eq)/peak if peak>0 else 0.0)
    return mdd

def month_concentration(daily):
    m=defaultdict(float)
    for d,r in daily: m[d[:7]] += r
    den=sum(abs(v) for v in m.values())
    return max((abs(v) for v in m.values()), default=0.0)/den if den else 0.0

def positive_years(daily):
    y=defaultdict(list)
    for d,r in daily: y[d[:4]].append(r)
    return sum(compounded(v)>0 for v in y.values())

def metrics(daily, trade_count):
    vals=[r for _,r in daily]
    return {"active_days":len(daily),"trades":trade_count,"net_mean_daily":mean(vals),"annualized_sharpe":sharpe(vals),"positive_calendar_years":positive_years(daily),"max_drawdown":max_drawdown(vals),"max_single_month_abs_pnl_concentration":month_concentration(daily),"compounded_return":compounded(vals)}

def passes(m,g):
    return m["active_days"]>=g["min_active_days"] and m["trades"]>=g["min_trades"] and m["net_mean_daily"]>g["net_mean_daily_gt"] and m["annualized_sharpe"]>=g["annualized_sharpe_gte"] and m["positive_calendar_years"]>=g["positive_calendar_years_gte"] and m["max_drawdown"]<=g["max_drawdown_lte"] and m["max_single_month_abs_pnl_concentration"]<=g["max_single_month_abs_pnl_concentration_lte"]

def robustness_pass(costm, delaym, g):
    return costm["net_mean_daily"]>g["cost_stress_net_mean_daily_gt"] and costm["annualized_sharpe"]>=g["cost_stress_annualized_sharpe_gte"] and delaym["net_mean_daily"]>g["delayed_execution_net_mean_daily_gt"] and delaym["annualized_sharpe"]>=g["delayed_execution_annualized_sharpe_gte"] and delaym["active_days"]>=g["delayed_execution_min_active_days"]

def signal(mech,row,volshock):
    body=(row["close"]-row["open"])/row["open"] if row["open"] else 0.0
    sign=1 if body>0 else -1 if body<0 else 0
    cl=(row["close"]-row["low"])/(row["high"]-row["low"]) if row["high"]>row["low"] else 0.5
    if mech=="BODY_CONTINUATION": return sign
    if mech=="BODY_REVERSAL": return -sign
    if mech=="CLOSE_LOCATION_CONTINUATION": return 1 if cl>=0.80 else -1 if cl<=0.20 else 0
    if mech=="CLOSE_LOCATION_REVERSAL": return -1 if cl>=0.80 else 1 if cl<=0.20 else 0
    if mech=="VOLUME_SHOCK_CONTINUATION": return sign if volshock is not None and volshock>=1.50 else 0
    if mech=="VOLUME_SHOCK_REVERSAL": return -sign if volshock is not None and volshock>=1.50 else 0
    return 0

def trade_return(prefix,sig,execrow,cost_mult=1.0):
    pv=POINT_VALUE[prefix]; gross=sig*(execrow["close"]-execrow["open"])*pv; notional=abs(execrow["open"])*pv
    return (gross-COST[prefix]*cost_mult)/notional if notional>0 else None

def bootstrap_mean_ci(vals, seed=20260904, block=5, n=1000):
    if not vals: return [0.0,0.0]
    rng=random.Random(seed); N=len(vals); means=[]
    for _ in range(n):
        out=[]
        while len(out)<N:
            s=rng.randrange(N)
            out.extend(vals[(s+i)%N] for i in range(block))
        means.append(mean(out[:N]))
    means.sort(); return [means[int(.025*(n-1))],means[int(.975*(n-1))]]

def load_rows(coverage_dir):
    blocks=sorted(Path(coverage_dir).glob("20??_Q?.json"))
    if len(blocks)!=20: raise RuntimeError(f"expected 20 coverage blocks, got {len(blocks)}")
    sessions=set(); rows=[]; identities=set(); dup=0
    for p in blocks:
        x=json.loads(p.read_text())
        if x.get("block_contract_pass") is not True: raise RuntimeError(f"coverage block not green: {p}")
        for day in x.get("rows",[]):
            if day.get("http_status")==200 and day.get("leaf_payloads"):
                sessions.add(day["date"])
            for r in day.get("market_rows",[]):
                key=(day["date"],r["ticker_symbol"],r["report_leaf_sha256"])
                if key in identities: dup+=1; continue
                identities.add(key); q=dict(r); q["date"]=day["date"]; rows.append(q)
    return sorted(sessions),rows,dup

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--coverage-dir",required=True); ap.add_argument("--gates",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
    gates=json.loads(Path(a.gates).read_text())
    sessions,rows,dup=load_rows(a.coverage_dir)
    sessions=[d for d in sessions if d!=KNOWN_GAP]
    spos={d:i for i,d in enumerate(sessions)}
    by_ticker=defaultdict(dict)
    for r in rows:
        if r["date"]==KNOWN_GAP: continue
        by_ticker[r["ticker_symbol"]][r["date"]]=r
    volhist=defaultdict(lambda: deque(maxlen=20)); observations=[]
    for d in sessions:
        for ticker,dm in by_ticker.items():
            r=dm.get(d)
            if not r: continue
            vh=volhist[ticker]; v=r.get("volume_or_traded_quantity"); vshock=None
            if v is not None and len(vh)>=10:
                sv=sorted(vh); med=sv[len(sv)//2] if len(sv)%2 else (sv[len(sv)//2-1]+sv[len(sv)//2])/2
                if med>0: vshock=v/med
            idx=spos[d]; n1=sessions[idx+1] if idx+1<len(sessions) else None; n2=sessions[idx+2] if idx+2<len(sessions) else None
            observations.append((d,ticker,r,dm.get(n1) if n1 else None,dm.get(n2) if n2 else None,vshock))
            if v is not None: vh.append(v)
    results={}
    for fid,(prefix,mech) in FAMILIES.items():
        buckets={"discovery":defaultdict(list),"discovery2x":defaultdict(list),"delayed":defaultdict(list),"replication":defaultdict(list)}
        counts=defaultdict(int)
        for d,ticker,r,n1,n2,vshock in observations:
            if not ticker.startswith(prefix): continue
            sig=signal(mech,r,vshock)
            if sig==0: continue
            if n1 is not None:
                rr=trade_return(prefix,sig,n1,1.0); rr2=trade_return(prefix,sig,n1,2.0)
                if rr is not None:
                    if "2022-01-01"<=d<="2024-12-31": buckets["discovery"][d].append(rr); buckets["discovery2x"][d].append(rr2); counts["discovery"]+=1
                    if "2020-01-01"<=d<="2021-12-31": buckets["replication"][d].append(rr); counts["replication"]+=1
            if n2 is not None and "2022-01-01"<=d<="2024-12-31":
                rd=trade_return(prefix,sig,n2,1.0)
                if rd is not None: buckets["delayed"][d].append(rd); counts["delayed"]+=1
        daily={k:sorted((d,mean(v)) for d,v in b.items()) for k,b in buckets.items()}
        md=metrics(daily["discovery"],counts["discovery"]); mc=metrics(daily["discovery2x"],counts["discovery"]); ml=metrics(daily["delayed"],counts["delayed"])
        discovery_pass=passes(md,gates["discovery_2022_2024"])
        robust_pass=discovery_pass and robustness_pass(mc,ml,gates["robustness"])
        mr=metrics(daily["replication"],counts["replication"]) if robust_pass else None
        repl_pass=bool(robust_pass and mr and passes(mr,gates["independent_replication_2020_2021"]))
        if counts["discovery"]==0: mortality="NO_TRADES"
        elif dup>0: mortality="SOURCE_QA_FAIL"
        elif repl_pass: mortality="SURVIVOR"
        else: mortality="SCIENTIFIC_REJECTION"
        results[fid]={"instrument":prefix,"mechanism":mech,"mortality":mortality,"bias_causality_qa_pass":dup==0,"discovery":{"metrics":md,"pass":discovery_pass},"robustness":{"cost_stress_metrics":mc,"delayed_execution_metrics":ml,"pass":robust_pass,"bootstrap_mean_95pct_ci":bootstrap_mean_ci([x for _,x in daily["discovery"]])},"replication":{"executed":robust_pass,"metrics":mr,"pass":repl_pass}}
    survivors=[f for f,x in results.items() if x["mortality"]=="SURVIVOR"]
    candidates=[]
    for prefix in ("WIN","WDO"):
        ss=[f for f in survivors if results[f]["instrument"]==prefix]
        ss.sort(key=lambda f:(-min(results[f]["robustness"]["cost_stress_metrics"]["annualized_sharpe"],results[f]["robustness"]["delayed_execution_metrics"]["annualized_sharpe"],results[f]["replication"]["metrics"]["annualized_sharpe"]),f))
        candidates.extend(ss[:1])
    out={"schema":"qrds.factory.b3_win_wdo_univariate_result.v1","generated_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"family_count":12,"results":results,"source_qa":{"coverage_blocks":20,"session_count":len(sessions),"market_row_count":len(rows),"duplicate_reduced_identity_count":dup,"known_gap_excluded":[KNOWN_GAP]},"replicated_survivors":survivors,"prospective_candidates":candidates,"final_survivor_status":"SURVIVOR_PRESENT" if survivors else "NULL — nenhum survivor válido","prospective_activation_performed":False,"prospective_credit":0,"scientific_credit":len(survivors),"safety":SAFETY}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"survivors":survivors,"prospective_candidates":candidates,"final_survivor_status":out["final_survivor_status"]},sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
