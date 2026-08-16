#!/usr/bin/env python3
"""Research-only prospective PIT/QOS/PRL50 three-track sidecar."""
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

CORE={"BTC","ETH","CASH"}; STRATEGIES=("QOS_Moderada","QOS_Ultra")

def req(x,msg):
    if not x: raise RuntimeError(msg)

def cj(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def shab(b): return hashlib.sha256(b).hexdigest()
def sharow(x): return shab(cj({k:v for k,v in x.items() if k not in {"row_sha256","state_sha256","anchor_sha256","result_sha256","blocked_sha256"}}).encode())
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write(p,x):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def contract(path):
    c=load(path); pit=c["point_in_time_universe"]; prl=c["prl50"]; s=c["safety"]
    req(c["schema"]=="gate-btc.qos-prospective-three-track.v1","contract schema drift")
    req(c["scope"]=="ALT_SLEEVE_SELECTOR_AND_EXIT_LAYER_ONLY","scope drift")
    req(float(pit["raw_coverage_reference_min"])==.95,"coverage reference drift")
    req(pit["raw_coverage_role"]=="DATA_QUALITY_DIAGNOSTIC_NOT_SIGNAL_ADMISSION_GATE","coverage role drift")
    req(pit["selector_inference_candidate_resolution"]=="ALL_FROZEN_CANDIDATES_MUST_HAVE_RESOLVED_MONTHLY_OUTCOME","selector resolution drift")
    req(pit["unresolved_candidate_policy"].startswith("BLOCK_SELECTOR_ALPHA"),"unresolved policy drift")
    req(c["price_source_policy"]["missing_control_price"].startswith("KEEP_IN_FROZEN_DENOMINATOR"),"missing control policy drift")
    req(c["terminal_outcome_policy"]["provisional_or_unresolved_terminal_return"]=="FORBIDDEN_TO_SYNTHESIZE","terminal synthesis drift")
    req(float(prl["activation_gain"])==.20 and float(prl["max_profit_giveback_fraction"])==.50 and prl["same_bar_exit"] is False,"PRL50 drift")
    req(s["research_only"] and s["shadow_only"] and s["not_approved"] and not s["engine_feed"] and not s["feeds_frozen_engine"],"safety drift")
    req(s["orders_generated"]==0 and s["real_capital_used"]==0,"capital/order drift")
    return c

def me(d): return (pd.Timestamp(d)+pd.offsets.MonthEnd(0)).normalize()
def nme(d): return (pd.Timestamp(d)+pd.offsets.MonthEnd(1)).normalize()
def zcsv(z,n): req(n in z.namelist(),f"missing {n}"); return pd.read_csv(io.BytesIO(z.read(n)))
def zjson(z,n): req(n in z.namelist(),f"missing {n}"); return json.loads(z.read(n))

def capture(v2a,c,day,upstream):
    day=pd.Timestamp(day).normalize(); first=pd.Timestamp(c["activation"]["first_eligible_signal_date"])
    req(day>=first and day==me(day),"ineligible signal date"); req(str(upstream).strip(),"snapshot id required")
    raw=Path(v2a).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=c["point_in_time_universe"]["required_files"]
        for n in names: req(n in z.namelist(),f"missing {n}")
        m=zjson(z,"outputs/v2a_run_manifest.json"); q=zcsv(z,"outputs/data_quality_summary.csv"); f=zcsv(z,"data/processed/qos_v2a_current_features.csv"); p=zcsv(z,"outputs/qos_v2a_current_portfolios.csv"); h=zcsv(z,"data/processed/qos_v2a_master_daily.csv"); hashes={n:shab(z.read(n)) for n in names}
    req(pd.Timestamp(str(m["data_as_of"])).normalize()==day,"V2A data_as_of mismatch"); req(len(q)==1,"quality row count")
    for col in ("is_core","is_stable","is_blocked"):
        req(col in f,"missing feature flag");
        if f[col].dtype!=bool: f[col]=f[col].astype(str).str.lower().map({"true":True,"false":False})
        req(f[col].notna().all(),f"invalid {col}")
    cand=sorted(set(f.loc[(~f.is_core)&(~f.is_stable)&(~f.is_blocked),"symbol"].astype(str).str.upper())); req(cand,"empty candidates")
    p["asset"]=p["asset"].astype(str).str.upper(); picks={}
    for st in STRATEGIES:
        x=p[(p.strategy.astype(str)==st)&(pd.to_numeric(p.weight,errors="coerce")>0)]
        a=sorted(set(x.asset)-CORE); req(a,f"empty picks {st}"); req(not(set(a)-set(cand)),f"picks outside PIT {st}"); picks[st]=a
    h["date"]=pd.to_datetime(h.date); h["symbol"]=h.symbol.astype(str).str.upper(); h=h[h.date<=day].sort_values(["symbol","date"])
    src={}
    for a in cand:
        x=h[h.symbol==a]; req(not x.empty,f"no source history {a}"); src[a]=str(x.iloc[-1].source)
    cov=float(q.iloc[0].coverage_ratio); ref=float(c["point_in_time_universe"]["raw_coverage_reference_min"])
    s={"schema":"gate-btc.qos-prospective-three-track.signal-state.v1","signal_date":day.date().isoformat(),"boundary_date":nme(day).date().isoformat(),"upstream_immutable_snapshot_id":str(upstream),"v2a_zip_sha256":shab(raw),"required_file_sha256":hashes,"v2a_version":str(m.get("version")),"raw_attempted_symbols":int(q.iloc[0].attempted_symbols),"raw_loaded_symbols":int(q.iloc[0].loaded_symbols),"raw_coverage_ratio":cov,"raw_coverage_reference_min":ref,"raw_coverage_quality":"HIGH_GE95" if cov>=ref else "LOW_LT95","admissible":True,"admission_reason":"PASS_STRUCTURAL_POINT_IN_TIME_CAPTURE","candidate_count":len(cand),"candidate_symbols":cand,"candidate_source_lock":src,"qos_picks":picks,"scope":c["scope"],"research_only":True,"shadow_only":True,"not_approved":True,"orders_generated":0,"real_capital_used":0}; s["state_sha256"]=sharow(s); return s

def init_archive(state,root):
    req(state.get("state_sha256")==sharow(state),"state hash mismatch"); root=Path(root)
    a={"schema":"gate-btc.qos-prospective-three-track.path-anchor.v1","signal_date":state["signal_date"],"boundary_date":state["boundary_date"],"signal_state_sha256":state["state_sha256"],"candidate_count":state["candidate_count"],"research_only":True,"orders_generated":0,"real_capital_used":0}; a["anchor_sha256"]=sharow(a); p=root/"ANCHOR.json"
    if p.exists(): req(load(p)==a,"anchor mutation")
    else: write(p,a)

def snaps(root): return sorted((Path(root)/"snapshots").glob("*.json"))

def append_path(state,root,master,day,runid):
    root=Path(root); init_archive(state,root); day=pd.Timestamp(day).normalize(); signal=pd.Timestamp(state["signal_date"]); req(day>=signal,"pre-signal path")
    old=snaps(root); prev=load(old[-1]) if old else None
    if prev:
        pd0=pd.Timestamp(prev["snapshot_date"]); req(prev["row_sha256"]==sharow(prev),"previous hash")
        if day!=pd0: req(day==pd0+pd.Timedelta(days=1),f"daily gap/backfill prohibited: prev={pd0.date()} current={day.date()}")
        prevsha=prev["prev_row_sha256"] if day==pd0 else prev["row_sha256"]
    else: req(day==signal,"first path must equal signal"); prevsha="GENESIS"
    x=master.copy(); req({"date","symbol","close_usd","source"}.issubset(x),"master columns"); x["date"]=pd.to_datetime(x.date).dt.normalize(); x["symbol"]=x.symbol.astype(str).str.upper(); x["close_usd"]=pd.to_numeric(x.close_usd,errors="coerce"); x=x[x.date==day]; req(not x.duplicated(["date","symbol"]).any(),"duplicate daily row"); xm={r.symbol:r for r in x.itertuples(index=False)}
    close={}; missing=[]
    for a in state["candidate_symbols"]:
        r=xm.get(a)
        if r is None or pd.isna(r.close_usd) or float(r.close_usd)<=0: missing.append(a); continue
        req(str(r.source)==str(state["candidate_source_lock"][a]),f"source substitution {a}"); close[a]={"close_usd":float(r.close_usd),"source":str(r.source)}
    row={"schema":"gate-btc.qos-prospective-three-track.path-daily.v1","snapshot_date":day.date().isoformat(),"source_run_id":str(runid),"signal_date":state["signal_date"],"signal_state_sha256":state["state_sha256"],"candidate_count":state["candidate_count"],"candidate_closes":dict(sorted(close.items())),"missing_candidates":sorted(missing),"observed_candidate_count":len(close),"prev_row_sha256":prevsha,"research_only":True,"orders_generated":0,"real_capital_used":0}; row["row_sha256"]=sharow(row); out=root/"snapshots"/f"{day.date().isoformat()}.json"
    if out.exists(): req(load(out)==row,"same-date revision/backfill"); return {"result":"DUPLICATE_IDENTICAL","missing_count":len(missing)}
    write(out,row); return {"result":"APPENDED","missing_count":len(missing)}

def archive_data(state,root):
    rows=[]; miss={}; prev="GENESIS"; expect=pd.Timestamp(state["signal_date"])
    for p in snaps(root):
        s=load(p); req(s["signal_state_sha256"]==state["state_sha256"] and s["prev_row_sha256"]==prev and s["row_sha256"]==sharow(s),"path chain invalid"); d=pd.Timestamp(s["snapshot_date"]); req(d==expect,"path calendar gap"); expect=d+pd.Timedelta(days=1); prev=s["row_sha256"]; miss[s["snapshot_date"]]=s.get("missing_candidates",[])
        for a,o in s.get("candidate_closes",{}).items(): rows.append({"date":d,"symbol":a,"close_usd":o["close_usd"],"source":o["source"]})
    req(miss,"empty archive"); return pd.DataFrame(rows),miss

def first_after(s,d):
    x=s[s.index>pd.Timestamp(d)]; req(not x.empty,f"no price after {d}"); return pd.Timestamp(x.index[0]),float(x.iloc[0])

def outcome(s,signal,boundary,act=.20,give=.50):
    s=s.sort_index().astype(float); ent,ep=first_after(s,signal); ex,xp=first_after(s,boundary); base=xp/ep-1; peak=-1e9; trig=None
    for d,p in s[(s.index>ent)&(s.index<=boundary)].items():
        g=float(p/ep-1); peak=max(peak,g)
        if peak>=act and g<=peak*(1-give): trig=pd.Timestamp(d); break
    if trig is None: px,pr=ex,base
    else: px,p=first_after(s,trig); pr=p/ep-1
    return {"entry_date":ent.date().isoformat(),"baseline_exit_date":ex.date().isoformat(),"baseline_return":float(base),"prl_trigger_date":trig.date().isoformat() if trig is not None else None,"prl_exit_date":px.date().isoformat(),"prl_return":float(pr)}

def evaluate(state,c,root):
    prices,miss=archive_data(state,root); latest=max(pd.Timestamp(d) for d in miss); boundary=pd.Timestamp(state["boundary_date"])
    if latest<=boundary: return "WAITING_CYCLE_COMPLETION",[],{"latest_snapshot_date":latest.date().isoformat()}
    pm={a:g.sort_values("date").set_index("date").close_usd for a,g in prices.groupby("symbol")}; control={}; unresolved=[]
    for a in state["candidate_symbols"]:
        try: control[a]=outcome(pm[a],state["signal_date"],boundary) if a in pm else (_ for _ in ()).throw(RuntimeError())
        except Exception: unresolved.append(a)
    if unresolved: return "WAITING_CANDIDATE_OUTCOME_RESOLUTION",[],{"unresolved_candidates":sorted(unresolved),"resolved_candidate_count":len(control),"candidate_count":state["candidate_count"],"latest_snapshot_date":latest.date().isoformat()}
    pit=float(np.mean([o["baseline_return"] for o in control.values()])); rows=[]; detail={"control_outcomes":control,"strategy_outcomes":{}}
    for st in STRATEGIES:
        os={a:control[a] for a in state["qos_picks"][st]}
        for a,o in os.items():
            ent=pd.Timestamp(o["entry_date"])
            for d,m in miss.items():
                if ent<pd.Timestamp(d)<=boundary and a in m: return "BLOCKED_SELECTED_DAILY_PATH_GAP",[],{"strategy":st,"symbol":a,"missing_date":d}
        qc=float(np.mean([o["baseline_return"] for o in os.values()])); qp=float(np.mean([o["prl_return"] for o in os.values()])); rows.append({"signal_date":state["signal_date"],"boundary_date":state["boundary_date"],"strategy":st,"pit_control_return":pit,"qos_control_return":qc,"qos_prl50_return":qp,"selector_alpha":qc-pit,"prl50_alpha":qp-qc,"package_delta":qp-pit,"selector_inference_status":"PASS_ALL_CANDIDATES_RESOLVED","raw_coverage_ratio_at_signal":state["raw_coverage_ratio"],"raw_coverage_quality_at_signal":state["raw_coverage_quality"],"candidate_count":state["candidate_count"],"selected_count":len(os),"research_only":True,"orders_generated":0,"real_capital_used":0}); detail["strategy_outcomes"][st]=os
    return "PASS_COMPLETED_CYCLE",rows,detail

def evaluate_cycle(state,c,prices):
    req(state.get("state_sha256")==sharow(state),"state hash mismatch"); x=prices.copy(); req({"date","symbol","close_usd","source"}.issubset(x),"price columns"); x["date"]=pd.to_datetime(x.date); x["symbol"]=x.symbol.astype(str).str.upper(); x["close_usd"]=pd.to_numeric(x.close_usd,errors="coerce"); x=x.dropna(subset=["date","symbol","close_usd","source"]); req(not x.duplicated(["date","symbol"]).any(),"duplicate prices")
    for a,g in x.groupby("symbol"):
        if a in state["candidate_source_lock"]: req(set(g.source.astype(str))=={str(state["candidate_source_lock"][a])},f"source substitution {a}")
    pm={a:g.sort_values("date").set_index("date").close_usd for a,g in x.groupby("symbol")}; boundary=pd.Timestamp(state["boundary_date"]); control={}; unresolved=[]
    for a in state["candidate_symbols"]:
        try: control[a]=outcome(pm[a],state["signal_date"],boundary) if a in pm else (_ for _ in ()).throw(RuntimeError())
        except Exception: unresolved.append(a)
    valid=not unresolved; pit=float(np.mean([o["baseline_return"] for o in control.values()])) if valid else None; rows=[]; detail={"control_outcomes":control,"unresolved_candidates":unresolved,"strategy_outcomes":{}}
    for st in STRATEGIES:
        os={}
        for a in state["qos_picks"][st]: req(a in pm,f"selected price history missing: {st} {a}"); os[a]=outcome(pm[a],state["signal_date"],boundary)
        qc=float(np.mean([o["baseline_return"] for o in os.values()])); qp=float(np.mean([o["prl_return"] for o in os.values()])); rows.append({"signal_date":state["signal_date"],"boundary_date":state["boundary_date"],"strategy":st,"pit_control_return":pit,"qos_control_return":qc,"qos_prl50_return":qp,"selector_alpha":qc-pit if valid else None,"prl50_alpha":qp-qc,"package_delta":qp-pit if valid else None,"selector_inference_status":"PASS_ALL_CANDIDATES_RESOLVED" if valid else "BLOCKED_UNRESOLVED_CANDIDATE_OUTCOMES","unresolved_candidate_count":len(unresolved),"control_path_coverage":len(control)/state["candidate_count"],"raw_coverage_ratio_at_signal":state["raw_coverage_ratio"],"raw_coverage_quality_at_signal":state["raw_coverage_quality"],"candidate_count":state["candidate_count"],"selected_count":len(os),"research_only":True,"orders_generated":0,"real_capital_used":0}); detail["strategy_outcomes"][st]=os
    return rows,detail


def append_results(path,rows,state_sha):
    path=Path(path); old=load(path) if path.exists() else []; prev="GENESIS"; seen=set()
    for r in old: req(r["prev_row_sha256"]==prev and r["row_sha256"]==sharow(r),"result chain invalid"); seen.add((r["signal_date"],r["strategy"])); prev=r["row_sha256"]
    for r in rows:
        k=(r["signal_date"],r["strategy"]); req(k not in seen,"duplicate cycle append forbidden"); x=dict(r,signal_state_sha256=state_sha,prev_row_sha256=prev); x["row_sha256"]=sharow(x); old.append(x); prev=x["row_sha256"]; seen.add(k)
    write(path,old)

def process(v2a,c,runtime,day,runid):
    day=pd.Timestamp(day).normalize(); first=pd.Timestamp(c["activation"]["first_eligible_signal_date"])
    if day<first: return {"status":"BEFORE_FIRST_SIGNAL_NOOP","snapshot_date":day.date().isoformat(),"research_only":True,"orders_generated":0,"real_capital_used":0}
    raw=Path(v2a).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z: m=zjson(z,"outputs/v2a_run_manifest.json"); master=zcsv(z,"data/processed/qos_v2a_master_daily.csv")
    req(pd.Timestamp(str(m["data_as_of"])).normalize()==day,"daily data_as_of mismatch"); runtime=Path(runtime); cycles=runtime/"cycles"; cycles.mkdir(parents=True,exist_ok=True); events=[]
    if day==me(day):
        cd=cycles/day.date().isoformat(); sp=cd/"SIGNAL_STATE.json"; ns=capture(v2a,c,day,f"v2a:{day.date()}:{shab(raw)}")
        if sp.exists(): req(load(sp)==ns,"same-signal revision"); cr="DUPLICATE_IDENTICAL"
        else: write(sp,ns); cr="CAPTURED"
        init_archive(ns,cd/"path"); events.append({"cycle":ns["signal_date"],"event":"SIGNAL","result":cr})
    for cd in sorted(x for x in cycles.iterdir() if x.is_dir()):
        sp=cd/"SIGNAL_STATE.json"; state=load(sp)
        if day<pd.Timestamp(state["signal_date"]) or (cd/"FINAL_RESULT.json").exists() or (cd/"BLOCKED.json").exists(): continue
        ar=append_path(state,cd/"path",master,day,runid); st,rows,detail=evaluate(state,c,cd/"path"); write(cd/"STATUS.json",{"schema":"gate-btc.qos-prospective-three-track.cycle-status.v1","cycle":state["signal_date"],"snapshot_date":day.date().isoformat(),"status":st,"path_append_result":ar["result"],"path_missing_count":ar["missing_count"],"detail":detail,"research_only":True,"orders_generated":0,"real_capital_used":0})
        if st=="PASS_COMPLETED_CYCLE":
            fr={"schema":"gate-btc.qos-prospective-three-track.final-result.v1","signal_state_sha256":state["state_sha256"],"completed_on_snapshot":day.date().isoformat(),"rows":rows,"detail":detail,"research_only":True,"orders_generated":0,"real_capital_used":0}; fr["result_sha256"]=sharow(fr); write(cd/"FINAL_RESULT.json",fr); append_results(runtime/"RESULT_LEDGER.json",rows,state["state_sha256"])
        elif st=="BLOCKED_SELECTED_DAILY_PATH_GAP":
            b={"schema":"gate-btc.qos-prospective-three-track.blocked.v1","signal_state_sha256":state["state_sha256"],"blocked_on_snapshot":day.date().isoformat(),"status":st,"detail":detail,"research_only":True,"orders_generated":0,"real_capital_used":0}; b["blocked_sha256"]=sharow(b); write(cd/"BLOCKED.json",b)
        events.append({"cycle":state["signal_date"],"event":"DAILY","append":ar["result"],"status":st})
    cs=[]
    for cd in sorted(x for x in cycles.iterdir() if x.is_dir()):
        s=load(cd/"SIGNAL_STATE.json"); st="COMPLETED" if (cd/"FINAL_RESULT.json").exists() else "BLOCKED" if (cd/"BLOCKED.json").exists() else load(cd/"STATUS.json")["status"] if (cd/"STATUS.json").exists() else "WAITING_FIRST_PATH"; cs.append({"signal_date":s["signal_date"],"status":st})
    status={"schema":"gate-btc.qos-prospective-three-track.runtime-status.v1","latest_snapshot_date":day.date().isoformat(),"cycles":cs,"result_ledger_rows":len(load(runtime/"RESULT_LEDGER.json")) if (runtime/"RESULT_LEDGER.json").exists() else 0,"research_only":True,"shadow_only":True,"not_approved":True,"orders_generated":0,"real_capital_used":0}; write(runtime/"STATUS.json",status); return {"status":"PASS_DAILY_PROCESS","snapshot_date":day.date().isoformat(),"events":events,"runtime":status}

sha_row=sharow
read_contract=contract
initialize_cycle_archive=init_archive
append_path_snapshot=append_path
evaluate_cycle_from_archive=evaluate
process_daily=process
append_ledger=append_results

def main():
    p=argparse.ArgumentParser(); p.add_argument("--contract",required=True); p.add_argument("--v2a-zip",required=True); p.add_argument("--runtime-dir",required=True); p.add_argument("--snapshot-date",required=True); p.add_argument("--source-run-id",required=True); a=p.parse_args(); print(json.dumps(process(Path(a.v2a_zip),contract(Path(a.contract)),Path(a.runtime_dir),a.snapshot_date,a.source_run_id),sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
