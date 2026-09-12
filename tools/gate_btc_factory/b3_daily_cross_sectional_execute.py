#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,statistics
from collections import defaultdict,deque
from datetime import datetime,timezone
from pathlib import Path
import b3_bluechips_univariate_execute as base

FAMILIES=[f"B3D{i:02d}" for i in range(1,7)]
FEATURE_BY_FAMILY={
 "B3D01":("body",1),"B3D02":("body",-1),
 "B3D03":("intraday_range",1),"B3D04":("intraday_range",-1),
 "B3D05":("volume_shock",1),"B3D06":("volume_shock",-1),
}

def feature_panel(rows,sessions,sidx):
    panel=defaultdict(list)
    by_ident={}
    for ident,rr in rows.items():
        by_date={r[0]:r for r in rr}; by_ident[ident]=by_date
        prior=deque(); prior_eligible_values=deque(maxlen=20)
        for r in rr:
            d,op,hi,lo,cl,trades,value=r; i=sidx[d]
            while prior and sidx[prior[0][0]] < i-60: prior.popleft()
            eligible=len(prior)>=45 and base.med([x[6] for x in prior])>=20_000_000 and base.med([x[5] for x in prior])>=500
            if eligible:
                vmed=base.med(prior_eligible_values) if len(prior_eligible_values)>=20 else None
                panel[d].append({
                  "ident":ident,
                  "body":(cl-op)/op,
                  "intraday_range":(hi-lo)/op,
                  "volume_shock":(value/vmed) if vmed else None
                })
                prior_eligible_values.append(value)
            prior.append(r)
    return panel,by_ident

def select_terciles(xs,feature):
    vals=[x for x in xs if x.get(feature) is not None]
    vals.sort(key=lambda x:(x[feature],x["ident"][0]))
    k=len(vals)//3
    if k<1:return [],[]
    return vals[:k],vals[-k:]

def build_positions(rows,sessions,sidx):
    panel,by_ident=feature_panel(rows,sessions,sidx)
    p1={f:defaultdict(list) for f in FAMILIES}; p2={f:defaultdict(list) for f in FAMILIES}
    for d,xs in panel.items():
        i=sidx[d]
        for fid,(feat,orientation) in FEATURE_BY_FAMILY.items():
            bottom,top=select_terciles(xs,feat)
            sides=[]
            for x in top:sides.append((x,1*orientation))
            for x in bottom:sides.append((x,-1*orientation))
            for x,sig in sides:
                hist=by_ident[x["ident"]]
                for lag,target in ((1,p1),(2,p2)):
                    if i+lag>=len(sessions):continue
                    ed=sessions[i+lag]; q=hist.get(ed)
                    if q is None:continue
                    gross=sig*((q[4]-q[1])/q[1])
                    target[fid][ed].append((sig,gross,x["ident"][0]))
    return p1,p2

def pass_disc(m,g):
    return m["active_days"]>=g["minimum_active_days"] and m["instrument_positions"]>=g["minimum_instrument_positions"] and m["mean_daily_net"]>g["primary_net_mean_daily_gt"] and m["annualized_sharpe"]>=g["primary_annualized_sharpe_gte"] and m["positive_calendar_years"]>=g["minimum_positive_calendar_years"] and m["max_drawdown"]<=g["max_drawdown_lte"] and m["month_concentration"]<=g["month_concentration_lte"]

def pass_rob(m40,md,g):
    return m40["mean_daily_net"]>g["cost_40bps_net_mean_daily_gt"] and m40["annualized_sharpe"]>=g["cost_40bps_annualized_sharpe_gte"] and md["mean_daily_net"]>g["delayed_t_plus_2_primary_net_mean_daily_gt"] and md["annualized_sharpe"]>=g["delayed_t_plus_2_primary_annualized_sharpe_gte"] and md["active_days"]>=g["delayed_t_plus_2_minimum_active_days"]

def pass_rep(m,g):
    return m["active_days"]>=g["minimum_active_days"] and m["instrument_positions"]>=g["minimum_instrument_positions"] and m["mean_daily_net"]>g["primary_net_mean_daily_gt"] and m["annualized_sharpe"]>=g["primary_annualized_sharpe_gte"] and m["positive_calendar_years"]>=g["minimum_positive_calendar_years"] and m["max_drawdown"]<=g["max_drawdown_lte"] and m["month_concentration"]<=g["month_concentration_lte"]

def clean(m): x=dict(m);x.pop("daily_returns",None);return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--capture-dir",required=True);ap.add_argument("--out",required=True)
    ap.add_argument("--prereg",default="tools/gate_btc_factory/B3_DAILY_CROSS_SECTIONAL_PREREG.v1.json")
    ap.add_argument("--gates",default="tools/gate_btc_factory/B3_DAILY_CROSS_SECTIONAL_GATES.v1.json")
    ap.add_argument("--hashes",default="tools/gate_btc_factory/B3_COTAHIST_FROZEN_HASHES.v1.json")
    a=ap.parse_args()
    prereg=json.loads(Path(a.prereg).read_text());g=json.loads(Path(a.gates).read_text());hashes=json.loads(Path(a.hashes).read_text())
    assert prereg["economics_read_for_this_family_block"] is False and g["economics_read_before_gate_freeze"] is False
    assert prereg["family_ids"]==FAMILIES
    rows,sessions,sidx=base.load_capture(Path(a.capture_dir),hashes)
    p1,p2=build_positions(rows,sessions,sidx)
    dd=base.window_sessions(sessions,*g["discovery_gate"]["window"]); rd=base.window_sessions(sessions,*g["replication_gate"]["window"])
    results={};survivors=[]
    for fid in FAMILIES:
        d30=base.metrics(p1[fid],dd,30);d40=base.metrics(p1[fid],dd,40);delay=base.metrics(p2[fid],dd,30)
        dp=pass_disc(d30,g["discovery_gate"]); rp=dp and pass_rob(d40,delay,g["robustness_gate"])
        item={"family_id":fid,"discovery":{"cost30":clean(d30),"cost40":clean(d40),"pass":dp},"robustness":{"delayed_t_plus_2_cost30":clean(delay),"pass":rp},"replication":None,"replicated_survivor":False,"mortality":None}
        if d30["instrument_positions"]==0:item["mortality"]="NO_TRADES"
        elif not rp:item["mortality"]="SCIENTIFIC_REJECTION"
        else:
            rm=base.metrics(p1[fid],rd,30); ok=pass_rep(rm,g["replication_gate"]); item["replication"]={"cost30":clean(rm),"pass":ok}
            if ok:item["replicated_survivor"]=True;survivors.append(fid)
            else:item["mortality"]="SCIENTIFIC_REJECTION"
        results[fid]=item
    out={"schema":"qrds.factory.b3_daily_cross_sectional_result.v1","frontier":"B3_DAILY_FRONTIER_V1","generated_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"family_count":6,"results":results,"replicated_survivors":survivors,"prospective_activation_performed":False,"economics_feedback_to_other_frontiers":False,"safety":prereg["safety"]}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PASS_EXECUTION","survivors":survivors,"orders":0,"real_capital":0},sort_keys=True))
if __name__=="__main__":main()
