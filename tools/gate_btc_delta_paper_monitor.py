#!/usr/bin/env python3
"""Append-only simulated monitor for the frozen GATE BTC Delta reconstruction.
Research/shadow only. No network, credentials, orders, or real capital path.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,os,zipfile
from datetime import date,timedelta,datetime,timezone
from pathlib import Path

SCHEMA="gate_btc.delta_paper_monitor.v1"; ZERO="0"*64
class MonitorError(RuntimeError): pass

def h(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def cj(x)->bytes:return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
def d(x)->date:return date.fromisoformat(str(x)[:10])
def f(x):return float(x or 0)
def b(x):return str(x).lower() in {"1","true","yes"}

def rows(raw:bytes):
    s=raw.decode("utf-8-sig"); return list(csv.DictReader(io.StringIO(s))) if s.strip() else []
def read_csv(p:Path):
    if not p.exists() or not p.read_text(encoding="utf-8-sig").strip(): return []
    with p.open(encoding="utf-8-sig",newline="") as z:return list(csv.DictReader(z))
def write_csv(p:Path,rs,fields):
    p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+".partial")
    with q.open("w",encoding="utf-8",newline="") as z:
        w=csv.DictWriter(z,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rs)
    os.replace(q,p)
def write_json(p:Path,x):
    p.parent.mkdir(parents=True,exist_ok=True); q=p.with_suffix(p.suffix+".partial")
    q.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False,default=str)+"\n",encoding="utf-8"); os.replace(q,p)

def member(z:zipfile.ZipFile,suffix:str,optional=False):
    m=[n for n in z.namelist() if n.endswith(suffix)]
    if optional and not m:return None
    if len(m)!=1:raise MonitorError(f"member {suffix}: found {len(m)}")
    return m[0]

def load(contract_path:Path,source_zip:Path):
    c=json.loads(contract_path.read_text(encoding="utf-8-sig"))
    if c.get("schema")!="gate_btc.delta_paper_monitor_contract.v1":raise MonitorError("bad contract")
    s=c["safety"]
    for k,v in {"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"exchange_auth_allowed":False,"orders_generated":0,"real_capital_used":0,"methodology_changes":0}.items():
        if s.get(k)!=v:raise MonitorError(f"unsafe contract {k}")
    raw=source_zip.read_bytes(); req=c["source_requirements"]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip():raise MonitorError("corrupt source zip")
        man=json.loads(z.read(member(z,req["manifest_suffix"])).decode("utf-8-sig"))
        if man.get("technical_status")!="PASS" or man.get("operational_status")!="NOT_APPROVED" or int(man.get("real_orders",0) or 0) or int(man.get("capital_used",0) or 0):raise MonitorError("unsafe/failed Delta source")
        out={"contract":c,"manifest":man,"zip_sha":h(raw)}
        for key in ("daily","trades","positions","selections","evidence_gate"):
            out[key]=rows(z.read(member(z,req[f"{key}_suffix"])))
        sn=member(z,req["selection_current_suffix"],True); rn=member(z,req["regime_suffix"],True)
        out["selection_current"]=json.loads(z.read(sn).decode("utf-8-sig")) if sn else {}
        out["regime"]=rows(z.read(rn)) if rn else []
    return out

def regime(src,asof):
    rr=[r for r in src["regime"] if str(r.get("date",""))[:10]==asof.isoformat()]
    r=rr[-1] if rr else src["selection_current"]
    return {"regime":r.get("regime"),"price_zone":r.get("price_zone"),"stabilization_confirmed":b(r.get("stabilization_confirmed")),"btc_close":f(r.get("btc_close"))}

def process(contract:Path,source_zip:Path,runtime:Path,run_id:str):
    src=load(contract,source_zip); c=src["contract"]; man=src["manifest"]
    asof,anchor,first=d(man["data_as_of"]),d(c["anchor_date"]),d(c["first_return_date"]); ss=c["strategies"]
    if asof<anchor:return {"status":"BEFORE_ANCHOR_NO_RUNTIME_WRITE","data_as_of":asof.isoformat()}
    runtime.mkdir(parents=True,exist_ok=True); status_p=runtime/"STATUS.json"; nav_p=runtime/"DAILY_NAV.csv"
    nav=read_csv(nav_p); old=json.loads(status_p.read_text()) if status_p.exists() else None
    if old:
        for k,v in {"research_only":True,"shadow_only":True,"not_approved":True,"orders_generated":0,"real_capital_used":0}.items():
            if old.get(k)!=v:raise MonitorError(f"unsafe runtime {k}")
    if asof==anchor and not nav:
        if old:
            return old
        ar={"schema":"gate_btc.delta_paper_monitor.anchor.v1","anchor_date":anchor.isoformat(),"source_run_id":str(run_id),"source_zip_sha256":src["zip_sha"],"initial_nav":1.0,"historical_economics_counted":False,"hypothesis_label":c["hypothesis_label"],"official_replica_claim":False}
        write_json(runtime/"ANCHOR.json",ar)
        st={"schema":SCHEMA,"status":"ARMED_WAITING_FIRST_RETURN","data_as_of":anchor.isoformat(),"anchor_date":anchor.isoformat(),"first_return_date":first.isoformat(),"observed_days":0,"hypothesis_label":c["hypothesis_label"],"official_replica_claim":False,"strategies":{s:{"normalized_nav":1.0,"drawdown":0.0} for s in ss},"btc_regime":regime(src,asof),"source_run_id":str(run_id),"source_zip_sha256":src["zip_sha"],"leaderboard_descriptive_only":True,"promotion_allowed":False,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders_generated":0,"real_capital_used":0,"methodology_changes":0}
        write_json(status_p,st); return st
    if asof==anchor:return old
    dates=sorted({d(r["date"]) for r in nav}); expected=(dates[-1]+timedelta(days=1)) if dates else first
    day={r["strategy"]:r for r in src["daily"] if str(r.get("date",""))[:10]==asof.isoformat() and r.get("strategy") in ss}
    if set(day)!=set(ss):raise MonitorError("missing strategy daily rows")
    econ=lambda s:{"date":asof.isoformat(),"strategy":s,"gross_return":f(day[s].get("gross_return")),"trading_cost_return":f(day[s].get("trading_cost_return")),"funding_return":f(day[s].get("funding_return")),"net_return":f(day[s].get("net_return")),"turnover":f(day[s].get("turnover")),"kill_switch_active":b(day[s].get("kill_switch_active"))}
    if asof<expected:
        accepted=[r for r in nav if r["date"]==asof.isoformat()]
        if len(accepted)!=len(ss):raise MonitorError("bad duplicate date")
        for r in accepted:
            if r["source_economic_row_sha256"]!=h(cj(econ(r["strategy"]))):raise MonitorError("conflicting revision")
        return old
    if asof>expected:raise MonitorError(f"gap: expected {expected}, got {asof}")
    state={s:{"nav":1.0,"peak":1.0} for s in ss}
    for r in nav:
        s=r["strategy"]; n=f(r["normalized_nav"]); state[s]={"nav":n,"peak":max(state[s]["peak"],n)}
    prev=nav[-1]["chain_sha256"] if nav else ZERO; new=[]; ev={r["strategy"]:r for r in src["evidence_gate"] if r.get("strategy") in ss}
    trades=[r for r in src["trades"] if str(r.get("date",""))[:10]==asof.isoformat() and r.get("strategy") in ss]
    poss=[r for r in src["positions"] if str(r.get("date",""))[:10]==asof.isoformat() and r.get("strategy") in ss]
    sels=[r for r in src["selections"] if str(r.get("execution_date",""))[:10]==asof.isoformat() and r.get("strategy") in ss]
    summary={}
    for s in ss:
        e=econ(s); n=state[s]["nav"]*(1+e["net_return"]); peak=max(state[s]["peak"],n); dd=n/peak-1
        r={**e,"normalized_nav":n,"drawdown":dd,"source_run_id":str(run_id),"source_zip_sha256":src["zip_sha"],"source_economic_row_sha256":h(cj(e)),"prev_chain_sha256":prev}
        r["chain_sha256"]=h(prev.encode()+cj(r)); prev=r["chain_sha256"]; new.append(r)
        q=ev.get(s,{})
        summary[s]={"normalized_nav":n,"drawdown":dd,"latest_net_return":e["net_return"],"latest_gross_return":e["gross_return"],"latest_trading_cost_return":e["trading_cost_return"],"latest_funding_return":e["funding_return"],"latest_turnover":e["turnover"],"trade_events_today":sum(x.get("strategy")==s for x in trades),"positions_today":sum(x.get("strategy")==s for x in poss),"evidence_eligible":b(q.get("evidence_eligible")),"evidence_rejection_reasons":q.get("rejection_reasons","")}
    fields=["date","strategy","gross_return","trading_cost_return","funding_return","net_return","turnover","kill_switch_active","normalized_nav","drawdown","source_run_id","source_zip_sha256","source_economic_row_sha256","prev_chain_sha256","chain_sha256"]
    write_csv(nav_p,nav+new,fields)
    for name,rs,datefield in (("TRADE_EVENTS.csv",trades,"date"),("POSITIONS_HISTORY.csv",poss,"date"),("SELECTIONS_HISTORY.csv",sels,"execution_date")):
        p=runtime/name; oldrs=read_csv(p); decorated=[]
        for x in rs:
            y=dict(x); y.update({"paper_monitor_date":asof.isoformat(),"source_run_id":str(run_id),"source_zip_sha256":src["zip_sha"]}); y["event_sha256"]=h(cj(y)); decorated.append(y)
        seen={x.get("event_sha256") for x in oldrs}; allrs=oldrs+[x for x in decorated if x["event_sha256"] not in seen]
        if allrs:write_csv(p,allrs,sorted({k for x in allrs for k in x}))
    chain_p=runtime/"SOURCE_CHAIN.csv"; chain=read_csv(chain_p); prev_src=chain[-1]["chain_sha256"] if chain else ZERO
    sr={"date":asof.isoformat(),"source_run_id":str(run_id),"source_zip_sha256":src["zip_sha"],"prev_chain_sha256":prev_src}; sr["chain_sha256"]=h(prev_src.encode()+cj(sr)); write_csv(chain_p,chain+[sr],list(sr))
    st={"schema":SCHEMA,"status":"ACTIVE_PROSPECTIVE_PAPER_SHADOW","generated_at_utc":datetime.now(timezone.utc).isoformat(),"data_as_of":asof.isoformat(),"anchor_date":anchor.isoformat(),"first_return_date":first.isoformat(),"observed_days":len(dates)+1,"hypothesis_label":c["hypothesis_label"],"official_replica_claim":False,"source_engine":c["source_engine"],"execution_caveat":c["execution_caveat"],"strategies":summary,"btc_regime":regime(src,asof),"source_run_id":str(run_id),"source_zip_sha256":src["zip_sha"],"latest_chain_sha256":new[-1]["chain_sha256"],"source_chain_sha256":sr["chain_sha256"],"trade_events_today":len(trades),"positions_today":len(poss),"selections_executed_today":len(sels),"leaderboard_descriptive_only":True,"promotion_allowed":False,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders_generated":0,"real_capital_used":0,"methodology_changes":0}
    write_json(status_p,st)
    lines=["# GATE BTC — Delta Prospective Paper Monitor","",f"Status: `{st['status']}`",f"Data as of: `{asof}`",f"Observed days: `{st['observed_days']}`","", "| Strategy | NAV | Daily net | DD |", "|---|---:|---:|---:|"]
    for s in ss:
        q=summary[s]; lines.append(f"| {s} | {q['normalized_nav']:.6f} | {q['latest_net_return']:+.4%} | {q['drawdown']:+.4%} |")
    lines += ["", "Research/shadow only; no orders or real capital. This monitors the GATE BTC reconstruction, not the proprietary/official Delta."]
    (runtime/"LATEST.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    return st

def main():
    p=argparse.ArgumentParser(); p.add_argument("--contract",type=Path,required=True); p.add_argument("--source-zip",type=Path,required=True); p.add_argument("--runtime-dir",type=Path,required=True); p.add_argument("--source-run-id",required=True); a=p.parse_args()
    r=process(a.contract,a.source_zip,a.runtime_dir,a.source_run_id); print(json.dumps({"status":r.get("status"),"data_as_of":r.get("data_as_of"),"observed_days":r.get("observed_days",0),"research_only":True,"orders_generated":0,"real_capital_used":0},indent=2)); return 0
if __name__=="__main__":raise SystemExit(main())
