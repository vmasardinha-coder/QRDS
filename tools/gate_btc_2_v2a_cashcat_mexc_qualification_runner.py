#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered CASHCAT/MEXC V2A source."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
API="https://api.mexc.com"; PAIR="CASHCATUSDT"; PROVIDER="MEXC"; LIMIT=1000

def req(path,params=None,retries=3):
    url=API+path+("?"+urllib.parse.urlencode(params) if params else ""); last=None
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"QRDS-GateBTC2-ResearchOnly/1"}),timeout=60) as r:return r.read()
        except Exception as e:last=e;time.sleep(2**i)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")
def parse_info(raw):
    o=json.loads(raw.decode()); syms=o.get("symbols") if isinstance(o,dict) else None
    if not isinstance(syms,list): raise ValueError("unexpected exchangeInfo")
    hits=[s for s in syms if s.get("symbol")==PAIR]
    if len(hits)!=1 or hits[0].get("baseAsset")!="CASHCAT" or hits[0].get("quoteAsset")!="USDT": raise ValueError("instrument identity mismatch")
    return hits[0]
def parse(raw):
    o=json.loads(raw.decode())
    if isinstance(o,dict): raise ValueError(f"unexpected MEXC error/envelope: {o}")
    if not isinstance(o,list): raise ValueError("unexpected MEXC payload")
    out=[]
    for x in o:
        if not isinstance(x,list) or len(x)<6: raise ValueError("schema mismatch")
        ts=int(x[0]); op,hi,lo,cl,bv=map(float,x[1:6]); qv=float(x[7]) if len(x)>7 else None
        if bv<0 or (qv is not None and qv<0): raise ValueError("negative volume")
        if not(lo<=min(op,cl)<=max(op,cl)<=hi): raise ValueError("OHLC invariant failed")
        out.append({"timestamp_ms":ts,"day":datetime.fromtimestamp(ts/1000,timezone.utc).date().isoformat(),"open":op,"high":hi,"low":lo,"close":cl,"base_volume":bv,"quote_volume":qv})
    return out
def main():
    p=argparse.ArgumentParser();p.add_argument("--end",required=True);p.add_argument("--output",default="artifacts/gate_btc_2/v2a_cashcat_mexc_qualification");p.add_argument("--max-pages",type=int,default=10);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True);ed=date.fromisoformat(a.end);cursor=int(datetime.combine(ed,datetime.max.time(),tzinfo=timezone.utc).timestamp()*1000)
    status="QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION";error=None;rows=[];pages=[];boundary=0;dup=0;gaps=[];mono=False;qa=False;info=None;info_sha=None
    try:
        raw=req("/api/v3/exchangeInfo",{"symbol":PAIR});info_sha=hashlib.sha256(raw).hexdigest();(out/"RAW_EXCHANGE_INFO.json").write_bytes(raw);info=parse_info(raw);allr=[];seen=set()
        for i in range(a.max_pages):
            params={"symbol":PAIR,"interval":"1d","endTime":str(cursor),"limit":str(LIMIT)};raw=req("/api/v3/klines",params);dig=hashlib.sha256(raw).hexdigest();(out/f"RAW_{i:03d}.json").write_bytes(raw);pr=parse(raw);acc=[r for r in pr if date.fromisoformat(r["day"])<=ed];ex=len(pr)-len(acc);boundary+=ex;pages.append({"page":i,"request":params,"sha256":dig,"raw_rows":len(pr),"accepted_rows":len(acc),"boundary_rows_excluded":ex})
            if not pr:break
            allr.extend(acc);old=min(r["timestamp_ms"] for r in pr)
            if old in seen:raise ValueError("pagination repeated oldest timestamp")
            seen.add(old);nxt=old-1
            if nxt>=cursor:raise ValueError("nondecreasing pagination cursor")
            cursor=nxt
            if len(pr)<LIMIT:break
        d={r["timestamp_ms"]:r for r in allr};rows=sorted(d.values(),key=lambda r:r["timestamp_ms"]);dup=len(allr)-len(rows)
        if not rows:raise ValueError("no in-window CASHCATUSDT historical candles returned")
        mono=all(rows[i]["timestamp_ms"]<rows[i+1]["timestamp_ms"] for i in range(len(rows)-1));have={r["day"] for r in rows};cur=date.fromisoformat(rows[0]["day"]);last=date.fromisoformat(rows[-1]["day"])
        while cur<=last:
            if cur.isoformat() not in have:gaps.append(cur.isoformat())
            cur+=timedelta(days=1)
        qa=mono and dup==0 and not gaps and date.fromisoformat(rows[-1]["day"])<=ed
    except Exception as e:status="FAIL_CLOSED_SOURCE_OR_PARSE_ERROR";error=str(e);rows=[];qa=False
    if not qa and status!="FAIL_CLOSED_SOURCE_OR_PARSE_ERROR":status="FAIL_CLOSED_FULL_CORPUS_QA"
    s={"schema_version":"GATE_BTC_2_V2A_CASHCAT_MEXC_QUALIFICATION_V1","issue":111,"symbol":"CASHCAT","coin_id":"cash-cat","provider":PROVIDER,"market":"SPOT","pair":PAIR,"status":status,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True,"qualification_only":True,"scientific_credit":False,"prospective_credit":False,"dataset_sealed":False,"promotion_allowed":False,"admission_scope":"NONE","retroactive_v2a_repair_allowed":False,"requested_end_utc":a.end,"timezone":"UTC","identity_sha256":info_sha,"instrument_identity":{"symbol":info.get("symbol") if info else None,"baseAsset":info.get("baseAsset") if info else None,"quoteAsset":info.get("quoteAsset") if info else None},"pages":pages,"physical_rows_ok":len(rows),"earliest_day":rows[0]["day"] if rows else None,"latest_day":rows[-1]["day"] if rows else None,"duplicate_rows":dup,"boundary_rows_excluded":boundary,"missing_days_within_returned_interval":gaps,"monotonic":mono,"qa_pass":qa,"historical_coverage_sufficiency_asserted":False,"source_qualification_outcome":"ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if qa else "FAIL_CLOSED_FULL_CORPUS_QA","error":error};(out/"CANDLES.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows));(out/"SUMMARY.json").write_text(json.dumps(s,indent=2,sort_keys=True)+"\n");print(json.dumps(s,indent=2,sort_keys=True));return 0 if qa else 2
if __name__=="__main__":raise SystemExit(main())
