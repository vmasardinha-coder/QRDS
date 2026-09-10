#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from collections import defaultdict
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo("America/Sao_Paulo"); UTC=timezone.utc
START="2025-01-01"; DISC_END="2025-12-31"; REPL_START="2026-01-01"; END="2026-08-09"
MIN_TOTAL=322; MIN_PART=161; NAMESPACE="RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"
WIN_RE=re.compile(r"^WIN[FGHJKMNQUVXZ]\d{2}$")
SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"MT5_READ_ONLY":True,"NO_ORDER_SEND":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_BACKFILL":True,"NO_LATE_SEAL":True,"NO_COUNTER_RESET":True,"NO_RETUNE":True,"FAIL_CLOSED":True,"H1_ECONOMICS_READ":False}

def cbytes(x): return (json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n").encode()
def digest(x): return hashlib.sha256(cbytes(x)).hexdigest()
def eligible(i):
    n=str(getattr(i,"name","")); d=str(getattr(i,"description","")).upper(); p=str(getattr(i,"path","")).upper()
    return bool(WIN_RE.fullmatch(n)) and "IBOVESPA MINI" in d and ("BVMF" in p or "B3" in p)
def meta(i): return {"symbol":str(i.name),"description":str(getattr(i,"description","")),"path":str(getattr(i,"path","")),"expiration_time":int(getattr(i,"expiration_time",0) or 0),"trade_mode":int(getattr(i,"trade_mode",0) or 0)}
def expiry_date(m):
    x=int(m.get("expiration_time") or 0); return datetime.fromtimestamp(x,tz=UTC).astimezone(TZ).date().isoformat() if x>0 else None
def choose_contract(session, metas):
    q=[(m["expiration_time"],m["symbol"]) for m in metas if expiry_date(m) and expiry_date(m)>=session]
    return sorted(q)[0][1] if q else None
def decode(epoch,mode):
    if mode=="UTC_EPOCH": return datetime.fromtimestamp(epoch,tz=UTC).astimezone(TZ)
    if mode=="BROKER_LOCAL_EPOCH": return datetime.fromtimestamp(epoch,tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
    raise RuntimeError("UNKNOWN_TIME_MODE")
def qtime(dt,mode):
    if mode=="UTC_EPOCH": return dt.astimezone(UTC)
    if mode=="BROKER_LOCAL_EPOCH": return dt.replace(tzinfo=None).replace(tzinfo=UTC)
    raise RuntimeError("UNKNOWN_TIME_MODE")
def tick_mode_evidence(mt5,symbols,now,scope):
    ev=[]
    for s in symbols:
        t=mt5.symbol_info_tick(s); e=int(getattr(t,"time",0) or 0) if t else 0
        if e<=0: continue
        u=datetime.fromtimestamp(e,tz=UTC).astimezone(TZ); l=datetime.fromtimestamp(e,tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
        du=abs((now-u).total_seconds()); dl=abs((now-l).total_seconds()); mode="UTC_EPOCH" if du<=dl else "BROKER_LOCAL_EPOCH"
        ev.append({"symbol":s,"scope":scope,"mode":mode,"delta_seconds":min(du,dl),"raw_tick_epoch":e})
    return ev
def detect_mode(mt5,symbols):
    now=datetime.now(TZ)
    ev=tick_mode_evidence(mt5,symbols,now,"EXACT_WIN_CONTRACTS")
    fresh=[x for x in ev if x["delta_seconds"]<=900]
    evidence_scope="EXACT_WIN_CONTRACTS"
    if not fresh:
        fallback=[]
        winset=set(symbols)
        for i in list(mt5.symbols_get() or []):
            s=str(getattr(i,"name",""))
            if not s or s in winset: continue
            x=tick_mode_evidence(mt5,[s],now,"SAME_MT5_TERMINAL_FALLBACK")
            if x:
                ev.extend(x)
                if x[0]["delta_seconds"]<=900:
                    fallback.append(x[0])
                    if len(fallback)>=64: break
        fresh=fallback
        evidence_scope="SAME_MT5_TERMINAL_FALLBACK"
    modes=sorted({x["mode"] for x in fresh})
    if len(modes)!=1: raise RuntimeError(f"AMBIGUOUS_MT5_TIME_MODE:{modes}:fresh={len(fresh)}:scope={evidence_scope}")
    return modes[0],{"selected_mode":modes[0],"evidence_scope":evidence_scope,"fresh_evidence_count":len(fresh),"current_tick_evidence":ev}
def norm(rows,symbol,mode):
    out=[]
    for r in ([] if rows is None else list(rows)):
        dt=decode(int(r["time"]),mode); d=dt.date().isoformat()
        if START<=d<=END:
            out.append({"symbol":symbol,"timestamp":dt.isoformat(),"epoch":int(r["time"]),"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),"tick_volume":int(r["tick_volume"]),"spread":int(r["spread"]),"real_volume":int(r["real_volume"])})
    return sorted(out,key=lambda x:(x["timestamp"],x["symbol"]))
def build_candidate(raw,metas):
    bucket=defaultdict(lambda:defaultdict(list))
    for s,rows in raw.items():
        for r in rows: bucket[r["timestamp"][:10]][s].append(r)
    cand=[]; qa=[]
    for day in sorted(bucket):
        sel=choose_contract(day,metas); rows=list(bucket[day].get(sel,[])) if sel else []
        ts=[datetime.fromisoformat(r["timestamp"]) for r in rows]; dup=len({r["timestamp"] for r in rows})!=len(rows)
        spacing=len(ts)>=2 and all(int((b-a).total_seconds())==300 for a,b in zip(ts,ts[1:])); valid=bool(sel) and not dup and len(rows)>=40 and spacing
        qa.append({"session":day,"selected_symbol":sel,"bar_count":len(rows),"duplicate":dup,"exact_300s_spacing":spacing,"structurally_valid":valid})
        if valid: cand.extend(rows)
    return cand,{"sessions":qa}
def counts(valid):
    s=set(valid); disc=sum(START<=d<=DISC_END for d in s); repl=sum(REPL_START<=d<=END for d in s)
    return {"total":len(s),"discovery":disc,"replication":repl}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out-dir",type=Path,required=True); a=ap.parse_args(); import MetaTrader5 as mt5
    a.out_dir.mkdir(parents=True,exist_ok=True)
    if not mt5.initialize(): raise RuntimeError(f"MT5_INITIALIZE_FAILED:{mt5.last_error()}")
    try:
        term=mt5.terminal_info(); acct=mt5.account_info(); metas=sorted([meta(x) for x in list(mt5.symbols_get(group="WIN*") or []) if eligible(x)],key=lambda x:x["symbol"])
        if not metas: raise RuntimeError("NO_EXACT_WIN_CONTRACTS_ENUMERATED")
        if any(expiry_date(m) is None for m in metas): raise RuntimeError("MISSING_EXPIRATION_METADATA")
        active=[]
        for m in metas:
            if mt5.symbol_select(m["symbol"],True):
                t=mt5.symbol_info_tick(m["symbol"])
                if t and int(getattr(t,"time",0) or 0)>0: active.append(m["symbol"])
        mode,te=detect_mode(mt5,active)
        sd=datetime.combine(datetime.fromisoformat(START).date(),time.min,tzinfo=TZ); ed=datetime.combine(datetime.fromisoformat(END).date(),time(23,59,59),tzinfo=TZ)
        raw={}; errors=[]
        for m in metas:
            s=m["symbol"]
            if not mt5.symbol_select(s,True): raw[s]=[]; errors.append({"symbol":s,"error":"SYMBOL_SELECT_FAILED"}); continue
            rr=mt5.copy_rates_range(s,mt5.TIMEFRAME_M5,qtime(sd,mode),qtime(ed,mode)); err=mt5.last_error(); raw[s]=norm(rr,s,mode)
            if rr is None: errors.append({"symbol":s,"error":str(err)})
        packet={"schema":"qrds.factory.invalidated_512.mt5_raw_capture.v1","namespace":NAMESPACE,"captured_at_utc":datetime.now(UTC).isoformat(),"window":{"discovery":{"start":START,"end":DISC_END},"replication":{"start":REPL_START,"end":END}},"time_mode":mode,"time_evidence":te,"terminal":{"name":str(getattr(term,"name","")),"company":str(getattr(term,"company","")),"connected":bool(getattr(term,"connected",False))},"account_server":str(getattr(acct,"server","")),"symbols":metas,"capture_errors":errors,"records_by_symbol":raw,"safety":SAFETY}; rh=digest(packet); packet["raw_capture_sha256"]=rh; (a.out_dir/"RAW_CAPTURE.json").write_bytes(cbytes(packet))
        cand,qa=build_candidate(raw,metas); valid=[x["session"] for x in qa["sessions"] if x["structurally_valid"]]; c=counts(valid); ch=hashlib.sha256(cbytes(cand)).hexdigest()
        gates={"identity_qa":True,"schema_qa":True,"timezone_qa":True,"chronology_qa":all(choose_contract(d,metas) for d in valid),"capacity_qa":c["total"]>=MIN_TOTAL and c["discovery"]>=MIN_PART and c["replication"]>=MIN_PART,"publication_semantics_proven":False,"revision_semantics_proven":False,"point_in_time_validity_proven":False,"independent_unseen_window_proven":True}
        green=all(gates.values()); result={"schema":"qrds.factory.invalidated_512.mt5_strict_v2_source_result.v1","authority_issue":693,"evaluation_namespace":NAMESPACE,"status":"SOURCE_GATE_GREEN" if green else "MT5_SOURCE_QUALIFICATION_FAIL_CLOSED","window":{"discovery":{"start":START,"end":DISC_END},"replication":{"start":REPL_START,"end":END}},"raw_capture_sha256":rh,"normalized_candidate_sha256":ch,"enumerated_exact_win_contract_count":len(metas),"raw_bar_count":sum(len(v) for v in raw.values()),"candidate_bar_count":len(cand),"valid_session_counts":c,"minimum_required":{"total":MIN_TOTAL,"discovery":MIN_PART,"replication":MIN_PART},"source_gates":gates,"capture_errors":errors,"source_admission_pass":green,"requalification_economics_allowed":green,"scientific_family_credit":0,"prospective_credit":0,"historical_backfill_credit":0,"safety":SAFETY}; result["result_sha256"]=digest(result)
        (a.out_dir/"CANDIDATE_M5.json").write_bytes(cbytes(cand)); (a.out_dir/"SESSION_QA.json").write_bytes(cbytes(qa)); (a.out_dir/"RESULT.json").write_bytes(cbytes(result)); print(json.dumps({k:result[k] for k in ("status","enumerated_exact_win_contract_count","raw_bar_count","candidate_bar_count","valid_session_counts","source_admission_pass")},sort_keys=True)); return 0
    finally: mt5.shutdown()
if __name__=="__main__": raise SystemExit(main())
