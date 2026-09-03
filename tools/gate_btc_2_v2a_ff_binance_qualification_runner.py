#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered FF/Binance V2A source."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API="https://api.binance.com"; PAIR="FFUSDT"; PROVIDER="BINANCE"; INTERVAL="1d"; LIMIT=1000

def request_bytes(path, params=None, retries=3):
    url=API+path+("?"+urllib.parse.urlencode(params) if params else "")
    last=None
    for attempt in range(retries):
        try:
            req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req,timeout=60) as r: return r.read()
        except Exception as exc:
            last=exc; time.sleep(2**attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")

def parse_exchange_info(raw):
    obj=json.loads(raw.decode())
    syms=obj.get("symbols") if isinstance(obj,dict) else None
    if not isinstance(syms,list) or len(syms)!=1: raise ValueError("unexpected Binance exchangeInfo payload")
    s=syms[0]
    if s.get("symbol")!=PAIR or s.get("baseAsset")!="FF" or s.get("quoteAsset")!="USDT": raise ValueError("instrument identity mismatch")
    return s

def parse_klines(raw):
    obj=json.loads(raw.decode())
    if isinstance(obj,dict): raise ValueError(f"unexpected Binance error/envelope: {obj}")
    if not isinstance(obj,list): raise ValueError("unexpected Binance kline payload")
    out=[]
    for row in obj:
        if not isinstance(row,list) or len(row)<6: raise ValueError("schema mismatch")
        ts=int(row[0]); o,h,l,c,bv=map(float,row[1:6]); qv=float(row[7]) if len(row)>7 else None
        if bv<0 or (qv is not None and qv<0): raise ValueError("negative volume")
        if not (l<=min(o,c)<=max(o,c)<=h): raise ValueError("OHLC invariant failed")
        out.append({"timestamp_ms":ts,"day":datetime.fromtimestamp(ts/1000,timezone.utc).date().isoformat(),"open":o,"high":h,"low":l,"close":c,"base_volume":bv,"quote_volume":qv})
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--end",required=True); ap.add_argument("--output",default="artifacts/gate_btc_2/v2a_ff_binance_qualification"); ap.add_argument("--max-pages",type=int,default=10); a=ap.parse_args()
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True); end_day=date.fromisoformat(a.end); end_ms=int(datetime.combine(end_day,datetime.max.time(),tzinfo=timezone.utc).timestamp()*1000)
    status="QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"; error=None; pages=[]; rows=[]; boundary=0; dup=0; gaps=[]; monotonic=False; qa=False; identity=None; identity_sha=None
    try:
        raw=request_bytes("/api/v3/exchangeInfo",{"symbol":PAIR}); identity_sha=hashlib.sha256(raw).hexdigest(); (out/"RAW_EXCHANGE_INFO.json").write_bytes(raw); identity=parse_exchange_info(raw)
        all_rows=[]; cursor=end_ms; seen=set()
        for i in range(a.max_pages):
            params={"symbol":PAIR,"interval":INTERVAL,"endTime":str(cursor),"limit":str(LIMIT)}; raw=request_bytes("/api/v3/klines",params); digest=hashlib.sha256(raw).hexdigest(); (out/f"RAW_KLINES_{i:03d}.json").write_bytes(raw); parsed=parse_klines(raw); accepted=[r for r in parsed if date.fromisoformat(r["day"])<=end_day]; ex=len(parsed)-len(accepted); boundary+=ex; pages.append({"page":i,"request":params,"sha256":digest,"raw_rows":len(parsed),"accepted_rows":len(accepted),"boundary_rows_excluded":ex})
            if not parsed: break
            all_rows.extend(accepted); oldest=min(r["timestamp_ms"] for r in parsed)
            if oldest in seen: raise ValueError("pagination repeated oldest timestamp")
            seen.add(oldest); nxt=oldest-1
            if nxt>=cursor: raise ValueError("nondecreasing pagination cursor")
            cursor=nxt
            if len(parsed)<LIMIT: break
        dedup={r["timestamp_ms"]:r for r in all_rows}; rows=sorted(dedup.values(),key=lambda r:r["timestamp_ms"]); dup=len(all_rows)-len(rows)
        if not rows: raise ValueError("no in-window FFUSDT historical candles returned")
        monotonic=all(rows[i]["timestamp_ms"]<rows[i+1]["timestamp_ms"] for i in range(len(rows)-1)); have={r["day"] for r in rows}; cur=date.fromisoformat(rows[0]["day"]); last=date.fromisoformat(rows[-1]["day"])
        while cur<=last:
            if cur.isoformat() not in have: gaps.append(cur.isoformat())
            cur+=timedelta(days=1)
        qa=monotonic and dup==0 and not gaps and date.fromisoformat(rows[-1]["day"])<=end_day
    except Exception as exc:
        status="FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"; error=str(exc); rows=[]; qa=False
    if not qa and status!="FAIL_CLOSED_SOURCE_OR_PARSE_ERROR": status="FAIL_CLOSED_FULL_CORPUS_QA"
    summary={"schema_version":"GATE_BTC_2_V2A_FF_BINANCE_QUALIFICATION_V1","issue":111,"symbol":"FF","coin_id":"falcon-finance-ff","provider":PROVIDER,"market":"SPOT","pair":PAIR,"status":status,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True,"qualification_only":True,"scientific_credit":False,"prospective_credit":False,"dataset_sealed":False,"promotion_allowed":False,"admission_scope":"NONE","retroactive_v2a_repair_allowed":False,"requested_end_utc":a.end,"timezone":"UTC","identity_sha256":identity_sha,"instrument_identity":{"symbol":identity.get("symbol") if identity else None,"baseAsset":identity.get("baseAsset") if identity else None,"quoteAsset":identity.get("quoteAsset") if identity else None,"status":identity.get("status") if identity else None},"pages":pages,"physical_rows_ok":len(rows),"earliest_day":rows[0]["day"] if rows else None,"latest_day":rows[-1]["day"] if rows else None,"duplicate_rows":dup,"boundary_rows_excluded":boundary,"missing_days_within_returned_interval":gaps,"monotonic":monotonic,"qa_pass":qa,"historical_coverage_sufficiency_asserted":False,"source_qualification_outcome":"ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if qa else "FAIL_CLOSED_FULL_CORPUS_QA","error":error}
    (out/"CANDLES.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in rows)); (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n"); print(json.dumps(summary,indent=2,sort_keys=True)); return 0 if qa else 2
if __name__=="__main__": raise SystemExit(main())
