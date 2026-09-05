#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json
from datetime import date,timedelta
from pathlib import Path
STRATEGIES=("QOS_Moderada","QOS_Ultra"); EXCLUDED={"BTC","ETH","CASH"}
def require(c,m):
    if not c: raise RuntimeError(m)
def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
def payload_sha(v,f):
    c=dict(v); c.pop(f,None); return hashlib.sha256(canonical_bytes(c)).hexdigest()
def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write_json(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def read_csv(p):
    with open(p,encoding="utf-8-sig",newline="") as h: return list(csv.DictReader(h))
def validate_contract(c):
    require(c["schema"]=="gate_btc.prl50_position_shadow_contract.v1","bad contract schema"); require(c["candidate_name"]=="PRL50_POSITION","candidate drift")
    require(c["candidate_definition"]["activation_gain"]==0.20,"activation drift"); require(c["candidate_definition"]["giveback_fraction_of_peak_profit"]==0.50,"giveback drift")
    require(c["first_eligible_signal_date"]=="2026-08-31","signal start drift"); require(c["first_eligible_execution_date"]=="2026-09-01","execution start drift")
    require(c["retrospective_backfill"]=="PROHIBITED","backfill guard drift"); require(c["name_collision_guard"]["must_remain_separate"] is True,"name collision guard drift"); require(c["research_only"] is True and c["engine_feed"] is False,"safety drift")
def snapshot_paths(d): return sorted((Path(d)/"snapshots").glob("*.json"))
def is_month_end(d): return (d+timedelta(days=1)).month!=d.month
def latest_month_end_signals(paths,before_day):
    for p in reversed(paths):
        r=load_json(p); d=date.fromisoformat(r["snapshot_date"])
        if d<before_day and is_month_end(d):
            s=r.get("active_signals") or r.get("signals")
            if s: return s
    return None
def write_status(d,a):
    ps=snapshot_paths(d); l=load_json(ps[-1]) if ps else None
    write_json(Path(d)/"STATUS.json",{"schema":"gate_btc.prl50_position_shadow_status.v1","status":"ACTIVE_PROSPECTIVE_ARCHIVE" if l else "WAITING_FIRST_UNTOUCHED_SIGNAL","candidate_name":"PRL50_POSITION","first_eligible_signal_date":a["first_eligible_signal_date"],"snapshot_count":len(ps),"latest_snapshot_date":l.get("snapshot_date") if l else None,"latest_row_sha256":l.get("row_sha256") if l else None,"active_signal_date":(l.get("active_signals",{}).get("QOS_Moderada",{}).get("signal_date") if l else None),"monthly_signal_policy":"MONTH_END_SIGNAL_HELD_UNTIL_NEXT_MONTH_END","contract_sha256":a["contract_sha256"],"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders_generated":0,"real_capital_used":0})
def initialize(cp,d):
    c=load_json(cp); validate_contract(c); d=Path(d); a={"schema":"gate_btc.prl50_position_shadow_anchor.v1","status":"WAITING_FIRST_UNTOUCHED_SIGNAL","candidate_name":"PRL50_POSITION","first_eligible_signal_date":c["first_eligible_signal_date"],"first_eligible_execution_date":c["first_eligible_execution_date"],"contract_sha256":file_sha(cp),"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders_generated":0,"real_capital_used":0}; a["anchor_sha256"]=payload_sha(a,"anchor_sha256"); p=d/"ANCHOR.json"
    if p.exists(): require(load_json(p)==a,"anchor mutation detected"); r="DUPLICATE_IDENTICAL"
    else: write_json(p,a); r="INITIALIZED"
    write_status(d,a); return {"result":r,**a}
def parse_signals(rows):
    out={}
    for s in STRATEGIES:
        sel=[r for r in rows if r.get("strategy")==s]; require(sel,f"missing {s}"); m={k:{r.get(k,"") for r in sel} for k in ("data_as_of","signal_period","execution_eligible_from","regime")}; require(all(len(v)==1 for v in m.values()),f"ambiguous signal metadata {s}")
        picks=[]
        for r in sel:
            a=r.get("asset","").strip(); w=float(r.get("weight") or 0)
            if a not in EXCLUDED and w>0: picks.append({"asset":a,"weight":w})
        require(picks,f"empty alt picks {s}"); out[s]={"strategy":s,"signal_date":next(iter(m["data_as_of"])),"signal_period":next(iter(m["signal_period"])),"execution_eligible_from":next(iter(m["execution_eligible_from"])),"regime":next(iter(m["regime"])),"picks":sorted(picks,key=lambda x:x["asset"])}
    return out
def exact_prices(rows,assets,sid):
    f={}
    for r in rows:
        if r.get("date")==sid and r.get("symbol") in assets:
            v=float(r["close_usd"]); require(v>0,f"invalid price {r.get('symbol')}"); f[r["symbol"]]=v
    miss=sorted(set(assets)-set(f)); require(not miss,f"missing exact snapshot prices: {miss}"); return dict(sorted(f.items()))
def append(cp,d,port,master,sid,run):
    c=load_json(cp); validate_contract(c); d=Path(d); a=load_json(d/"ANCHOR.json"); require(a["contract_sha256"]==file_sha(cp),"contract differs from anchor"); sd=date.fromisoformat(sid); fs=date.fromisoformat(c["first_eligible_signal_date"])
    if sd<fs: return {"result":"BEFORE_FIRST_SIGNAL_NOOP","snapshot_date":sid}
    op=d/"snapshots"/f"{sid}.json"
    if op.exists():
        e=load_json(op); require(e.get("source_run_id")==str(run),"duplicate source run mismatch"); require(e.get("current_portfolios_sha256")==file_sha(port),"duplicate portfolio source mismatch"); require(e.get("master_daily_sha256")==file_sha(master),"duplicate master source mismatch"); require(e.get("row_sha256")==payload_sha(e,"row_sha256"),"duplicate row hash invalid"); return {"result":"DUPLICATE_IDENTICAL","snapshot_date":sid,"row_sha256":e["row_sha256"],"price_count":len(e.get("selected_alt_closes",{}))}
    ps=snapshot_paths(d); prev=load_json(ps[-1]) if ps else None
    if prev is None: require(sd==fs,"first prospective record must be exact first eligible signal date; backfill prohibited"); psha=None
    else:
        pd=date.fromisoformat(prev["snapshot_date"]); require(sd==pd+timedelta(days=1),f"daily gap/backfill prohibited: prev={pd} current={sd}"); require(prev["row_sha256"]==payload_sha(prev,"row_sha256"),"previous row hash invalid"); psha=prev["row_sha256"]
    obs=parse_signals(read_csv(port))
    for s,x in obs.items(): require(date.fromisoformat(x["signal_date"])>=fs,f"pre-freeze signal still active for {s}; mid-cycle initialization prohibited"); require(date.fromisoformat(x["execution_eligible_from"])>date.fromisoformat(x["signal_date"]),"non-lagged signal")
    if prev is None or is_month_end(sd): active=obs; changed=True
    else:
        active=prev.get("active_signals") or latest_month_end_signals(ps,sd); require(active,"missing active monthly signal"); changed=False
    assets={p["asset"] for s in active.values() if date.fromisoformat(s["execution_eligible_from"])<=sd for p in s["picks"]}; prices=exact_prices(read_csv(master),assets,sid) if assets else {}
    row={"schema":"gate_btc.prl50_position_shadow_daily.v1","snapshot_date":sid,"source_run_id":str(run),"candidate_name":"PRL50_POSITION","signals":obs,"active_signals":active,"active_signal_changed":changed,"selected_alt_closes":prices,"current_portfolios_sha256":file_sha(port),"master_daily_sha256":file_sha(master),"previous_row_sha256":psha,"contract_sha256":a["contract_sha256"],"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders_generated":0,"real_capital_used":0}; row["row_sha256"]=payload_sha(row,"row_sha256"); write_json(op,row); write_status(d,a); return {"result":"APPENDED","snapshot_date":sid,"row_sha256":row["row_sha256"],"price_count":len(prices),"active_signal_changed":changed}
def main():
    p=argparse.ArgumentParser(); s=p.add_subparsers(dest="command",required=True); i=s.add_parser("initialize"); i.add_argument("--contract",required=True); i.add_argument("--ledger-dir",required=True); x=s.add_parser("append"); x.add_argument("--contract",required=True); x.add_argument("--ledger-dir",required=True); x.add_argument("--current-portfolios",required=True); x.add_argument("--master-daily",required=True); x.add_argument("--snapshot-id",required=True); x.add_argument("--source-run-id",required=True); a=p.parse_args(); r=initialize(a.contract,a.ledger_dir) if a.command=="initialize" else append(a.contract,a.ledger_dir,a.current_portfolios,a.master_daily,a.snapshot_id,a.source_run_id); print(json.dumps(r,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
