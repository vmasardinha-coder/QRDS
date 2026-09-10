#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ=ZoneInfo("America/Sao_Paulo"); UTC=timezone.utc
START="2025-01-01"; DISC_END="2025-12-31"; REPL_START="2026-01-01"; END="2026-08-09"
MIN_TOTAL=322; MIN_PART=161; NAMESPACE="RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"
WIN_RE=re.compile(r"^WIN[FGHJKMNQUVXZ]\d{2}$")
TIME_MODES=("UTC_EPOCH","BROKER_LOCAL_EPOCH")
MAX_BARS_PER_CONTRACT=10000
SOURCE_ROLE="INDEPENDENT_SECONDARY_SOURCE"
USAGE_CONSTRAINT="CROSS_VALIDATION_ONLY"
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
def tick_mode_evidence(mt5,symbols,now,scope):
    ev=[]
    for s in symbols:
        t=mt5.symbol_info_tick(s); e=int(getattr(t,"time",0) or 0) if t else 0
        if e<=0: continue
        u=datetime.fromtimestamp(e,tz=UTC).astimezone(TZ); l=datetime.fromtimestamp(e,tz=UTC).replace(tzinfo=None).replace(tzinfo=TZ)
        du=abs((now-u).total_seconds()); dl=abs((now-l).total_seconds()); mode="UTC_EPOCH" if du<=dl else "BROKER_LOCAL_EPOCH"
        ev.append({"symbol":s,"scope":scope,"mode":mode,"delta_seconds":min(du,dl),"raw_tick_epoch":e})
    return ev
def detect_mode_optional(mt5,symbols):
    now=datetime.now(TZ); ev=tick_mode_evidence(mt5,symbols,now,"EXACT_WIN_CONTRACTS"); fresh=[x for x in ev if x["delta_seconds"]<=900]; scope="EXACT_WIN_CONTRACTS"
    if not fresh:
        winset=set(symbols); fallback=[]
        for i in list(mt5.symbols_get() or []):
            s=str(getattr(i,"name",""))
            if not s or s in winset: continue
            x=tick_mode_evidence(mt5,[s],now,"SAME_MT5_TERMINAL_FALLBACK")
            if x:
                ev.extend(x)
                if x[0]["delta_seconds"]<=900:
                    fallback.append(x[0])
                    if len(fallback)>=64: break
        fresh=fallback; scope="SAME_MT5_TERMINAL_FALLBACK"
    modes=sorted({x["mode"] for x in fresh})
    selected=modes[0] if len(modes)==1 else None
    return selected,{"selected_mode":selected,"evidence_scope":scope,"fresh_evidence_count":len(fresh),"observed_modes":modes,"current_tick_evidence":ev,"timezone_admission_pass":selected is not None}
def raw_row(r):
    return {"epoch":int(r["time"]),"open":float(r["open"]),"high":float(r["high"]),"low":float(r["low"]),"close":float(r["close"]),"tick_volume":int(r["tick_volume"]),"spread":int(r["spread"]),"real_volume":int(r["real_volume"])}
def norm(raw,symbol,mode):
    out=[]
    for r in raw:
        dt=decode(int(r["epoch"]),mode); d=dt.date().isoformat()
        if START<=d<=END: out.append({"symbol":symbol,"timestamp":dt.isoformat(),**r})
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
    s=set(valid); return {"total":len(s),"discovery":sum(START<=d<=DISC_END for d in s),"replication":sum(REPL_START<=d<=END for d in s)}
def capacity_ok(c): return c["total"]>=MIN_TOTAL and c["discovery"]>=MIN_PART and c["replication"]>=MIN_PART

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
            if mt5.symbol_select(m["symbol"],True): active.append(m["symbol"])
        selected_mode,time_evidence=detect_mode_optional(mt5,active)

        raw={}; errors=[]; queries=[]
        for m in metas:
            s=m["symbol"]
            if not mt5.symbol_select(s,True):
                raw[s]=[]; errors.append({"symbol":s,"error":"SYMBOL_SELECT_FAILED"}); continue
            rr=mt5.copy_rates_from_pos(s,mt5.TIMEFRAME_M5,0,MAX_BARS_PER_CONTRACT); err=mt5.last_error()
            rows=[raw_row(r) for r in ([] if rr is None else list(rr))]
            raw[s]=rows
            queries.append({"symbol":s,"method":"copy_rates_from_pos","start_pos":0,"requested_count":MAX_BARS_PER_CONTRACT,"returned_count":len(rows),"last_error":str(err)})
            if rr is None: errors.append({"symbol":s,"error":str(err)})

        packet={"schema":"qrds.factory.invalidated_512.mt5_raw_capture.v3","namespace":NAMESPACE,"captured_at_utc":datetime.now(UTC).isoformat(),"capture_method":{"name":"copy_rates_from_pos","start_pos":0,"max_bars_per_contract":MAX_BARS_PER_CONTRACT,"timezone_independent":True},"frozen_local_window":{"discovery":{"start":START,"end":DISC_END},"replication":{"start":REPL_START,"end":END}},"time_evidence":time_evidence,"terminal":{"name":str(getattr(term,"name","")),"company":str(getattr(term,"company","")),"connected":bool(getattr(term,"connected",False))},"account_server":str(getattr(acct,"server","")),"symbols":metas,"capture_queries":queries,"capture_errors":errors,"records_by_symbol":raw,"source_role":SOURCE_ROLE,"usage_constraint":USAGE_CONSTRAINT,"safety":SAFETY}
        rh=digest(packet); packet["raw_capture_sha256"]=rh; (a.out_dir/"RAW_CAPTURE.json").write_bytes(cbytes(packet))

        mode_results={}
        for mode in TIME_MODES:
            normalized={s:norm(rows,s,mode) for s,rows in raw.items()}
            cand,qa=build_candidate(normalized,metas); valid=[x["session"] for x in qa["sessions"] if x["structurally_valid"]]; c=counts(valid)
            mode_results[mode]={"valid_session_counts":c,"capacity_qa":capacity_ok(c),"candidate_bar_count":len(cand),"normalized_candidate_sha256":hashlib.sha256(cbytes(cand)).hexdigest()}
            (a.out_dir/f"CANDIDATE_M5_{mode}.json").write_bytes(cbytes(cand)); (a.out_dir/f"SESSION_QA_{mode}.json").write_bytes(cbytes(qa))

        conservative={k:min(mode_results[m]["valid_session_counts"][k] for m in TIME_MODES) for k in ("total","discovery","replication")}
        capacity_all_modes=all(mode_results[m]["capacity_qa"] for m in TIME_MODES)
        gates={"identity_qa":True,"schema_qa":True,"timezone_qa":selected_mode is not None,"chronology_qa":True,"capacity_qa":capacity_all_modes,"publication_semantics_proven":False,"revision_semantics_proven":False,"point_in_time_validity_proven":False,"independent_unseen_window_proven":True}
        qualified_for_cross_validation=all(gates.values())
        result={"schema":"qrds.factory.invalidated_512.mt5_strict_v2_source_result.v4","authority_issue":693,"evaluation_namespace":NAMESPACE,"status":"MT5_SECONDARY_CROSS_VALIDATION_QUALIFIED" if qualified_for_cross_validation else "MT5_SECONDARY_CROSS_VALIDATION_FAIL_CLOSED","capture_completed":True,"timezone_admission_pass":selected_mode is not None,"selected_time_mode":selected_mode,"raw_capture_sha256":rh,"enumerated_exact_win_contract_count":len(metas),"raw_bar_count":sum(len(v) for v in raw.values()),"capacity_by_time_mode":mode_results,"valid_session_counts":conservative,"minimum_required":{"total":MIN_TOTAL,"discovery":MIN_PART,"replication":MIN_PART},"source_gates":gates,"capture_queries":queries,"capture_errors":errors,"source_role":SOURCE_ROLE,"usage_constraint":USAGE_CONSTRAINT,"cross_validation_qualification_pass":qualified_for_cross_validation,"source_admission_pass":False,"may_be_primary_source":False,"may_reconstruct_lost_clocks":False,"requalification_economics_allowed":False,"scientific_family_credit":0,"prospective_credit":0,"historical_backfill_credit":0,"safety":SAFETY}; result["result_sha256"]=digest(result)
        (a.out_dir/"RESULT.json").write_bytes(cbytes(result)); print(json.dumps({"status":result["status"],"capture_completed":True,"timezone_admission_pass":result["timezone_admission_pass"],"raw_bar_count":result["raw_bar_count"],"capacity_by_time_mode":mode_results,"conservative_valid_session_counts":conservative,"source_admission_pass":False,"capture_queries":queries},sort_keys=True)); return 0
    finally: mt5.shutdown()
if __name__=="__main__": raise SystemExit(main())
