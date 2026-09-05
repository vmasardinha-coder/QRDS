#!/usr/bin/env python3
"""Bounded retry for the mechanically unresolved members of preregistered batch #542."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
UA="QRDS-GateBTC2-ResearchOnly/1"; END=date(2026,9,4); START=END-timedelta(days=32)
TARGETS={"REUSD":("eth","0xb96cee75211700bc148b95b1c907d726791f4457","REUSD","USDT"),"CRVUSD":("eth","0x4dece678ceceb27446b35c672dc7d61f30bad69e","CRVUSD","USDC"),"EURCV":("eth","0x1f195908f2ee7a6fc15d33b30c82298f568e805c","EURCV","USDC")}
def req(url,retries=7):
    last=None
    for n in range(retries):
        try:
            r=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA,"Accept-Version":"20230302"})
            with urllib.request.urlopen(r,timeout=60) as resp:return resp.read()
        except Exception as exc:last=exc; time.sleep(min(60,3*(2**n)))
    raise RuntimeError(f"request failed after {retries} attempts: {url}: {last}")
def dump(out,name,raw): (out/name).write_bytes(raw); return hashlib.sha256(raw).hexdigest()
def day(ts):return datetime.fromtimestamp(ts,timezone.utc).date().isoformat()
def valid(o,h,l,c,v):return all(x==x for x in (o,h,l,c,v)) and v>=0 and not(o==h==l==c==0) and l<=min(o,c)<=max(o,c)<=h
def assess(rows):
    rows=sorted(rows,key=lambda x:x["timestamp"]); have={r["day"] for r in rows}; missing=[]; cur=START
    while cur<=END:
        if cur.isoformat() not in have:missing.append(cur.isoformat())
        cur+=timedelta(days=1)
    ts=[r["timestamp"] for r in rows]; dup=len(ts)-len(set(ts)); mono=all(ts[i]<ts[i+1] for i in range(len(ts)-1)); return {"physical_rows_ok":len(rows),"missing_days_in_requested_window":missing,"duplicate_rows":dup,"monotonic":mono,"qa_pass":len(rows)==33 and not missing and dup==0 and mono}
def token_symbols(payload):return {str((x.get("attributes") or {}).get("symbol","")).upper() for x in payload.get("included") or [] if x.get("type")=="token"}
def gecko(symbol,cfg,out):
    net,pool,base,quote=cfg; api="https://api.geckoterminal.com/api/v2"; ident_raw=req(f"{api}/networks/{net}/pools/{pool}?include=base_token,quote_token"); ident=json.loads(ident_raw); syms=token_symbols(ident); sha1=dump(out,"RAW_POOL.json",ident_raw)
    if base not in syms or quote not in syms:raise ValueError(f"pool token mismatch {sorted(syms)}")
    time.sleep(12); end_ts=int(datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1; q=urllib.parse.urlencode({"aggregate":1,"before_timestamp":end_ts,"limit":33,"currency":"usd"}); raw=req(f"{api}/networks/{net}/pools/{pool}/ohlcv/day?{q}"); sha2=dump(out,"RAW_OHLCV.json",raw); series=((((json.loads(raw).get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or []); rows=[]
    for x in series:
        if len(x)<6:continue
        ts=int(x[0]); d=date.fromisoformat(day(ts)); o,h,l,c,v=map(float,x[1:6])
        if START<=d<=END:
            if not valid(o,h,l,c,v):raise ValueError("OHLC/volume invariant failed")
            rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
    return rows,{"provider":"GECKOTERMINAL_PUBLIC_ONCHAIN","source_identity":f"{net}:{pool}","pool_token_symbols":sorted(syms),"raw_sha256":{"pool":sha1,"ohlcv":sha2}}
def ausd(out):
    api="https://api.kraken.com/0/public"; pairs_raw=req(f"{api}/AssetPairs"); pairs=json.loads(pairs_raw); dump(out,"RAW_PAIRS.json",pairs_raw); hits=[]
    for key,obj in (pairs.get("result") or {}).items():
        alt=str(obj.get("altname","")).upper(); ws=str(obj.get("wsname","")).upper(); base=str(obj.get("base","")).upper().lstrip("XZ"); quote=str(obj.get("quote","")).upper().lstrip("XZ")
        if ws=="AUSD/USD" or (base=="AUSD" and quote=="USD") or (alt=="AUSDUSD"):hits.append((key,obj))
    exact=[x for x in hits if str(x[1].get("wsname","")).upper()=="AUSD/USD"]
    if len(exact)!=1:raise ValueError(f"Kraken canonical wsname AUSD/USD not unique: {len(exact)}; all candidates={len(hits)}")
    key,ident=exact[0]; pair=str(ident.get("altname") or key); since=int(datetime.combine(START,datetime.min.time(),tzinfo=timezone.utc).timestamp()); raw=req(f"{api}/OHLC?"+urllib.parse.urlencode({"pair":pair,"interval":1440,"since":since})); dump(out,"RAW_OHLCV.json",raw); payload=json.loads(raw); series=next((v for k,v in (payload.get("result") or {}).items() if k!="last" and isinstance(v,list)),[]); rows=[]
    for x in series:
        if len(x)<7:continue
        ts=int(x[0]); d=date.fromisoformat(day(ts)); o,h,l,c,v=map(float,[x[1],x[2],x[3],x[4],x[6]])
        if START<=d<=END and valid(o,h,l,c,v):rows.append({"timestamp":ts,"day":d.isoformat(),"open":o,"high":h,"low":l,"close":c,"volume":v})
    return rows,{"provider":"KRAKEN","source_identity":pair,"identity":ident,"identity_resolution":"UNIQUE_CANONICAL_WSNAME_AUSD_USD_FROM_PREREGISTERED_MARKET","candidate_count_before_canonical_key":len(hits)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);results=[]
    for symbol in ["AUSD","REUSD","CRVUSD","EURCV"]:
        out=a.output/symbol.lower();out.mkdir(exist_ok=True);error=None;meta={};rows=[]
        try:
            rows,meta=ausd(out) if symbol=="AUSD" else gecko(symbol,TARGETS[symbol],out);qa=assess(rows);status="QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION" if qa["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA"
        except Exception as exc:error=str(exc);qa=assess([]);status="FAIL_CLOSED_MECHANICAL_OR_IDENTITY"
        s={"symbol":symbol,"status":status,"error":error,**meta,**qa,"source_admitted":False,"d0_credit":0,"scientific_credit":False,"prospective_credit":False};(out/"SUMMARY.json").write_text(json.dumps(s,indent=2,sort_keys=True)+"\n");results.append(s);time.sleep(15)
    summary={"schema_version":"GATE_BTC_2_V2A_SOURCE_BATCH_RETRY_V1","date":"2026-09-05","targets":["AUSD","REUSD","CRVUSD","EURCV"],"results":[{"symbol":x["symbol"],"status":x["status"],"qa_pass":x["qa_pass"],"error":x["error"]} for x in results],"source_admission_changed":False,"d0_started":False,"scientific_credit":False,"prospective_credit":False,"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL_BRL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"NO_SILENT_SOURCE_SUBSTITUTION":True,"FAIL_CLOSED":True};(a.output/"BATCH_SUMMARY.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n");print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=="__main__":main()
