#!/usr/bin/env python3
"""Fail-closed physical qualification for preregistered SOFID on Kraken.

Qualification-only. Discovers the exact public Kraken asset/pair before reading
OHLC. Raw responses and SHA-256 are preserved. No source admission, D0,
prospective/scientific credit, backfill, engine feed, orders or capital.
"""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE="https://api.kraken.com/0/public"
UA="QRDS-GateBTC2-ResearchOnly/1"

def get(path, params=None, retries=3):
    url=BASE+path
    if params: url += "?"+urllib.parse.urlencode(params)
    last=None
    for n in range(retries):
        try:
            req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":UA})
            with urllib.request.urlopen(req,timeout=60) as r: return url,r.read()
        except Exception as exc:
            last=exc; time.sleep(2**n)
    raise RuntimeError(f"Kraken request failed: {last}")

def decode(raw):
    obj=json.loads(raw.decode())
    if not isinstance(obj,dict) or obj.get("error"):
        raise ValueError(f"Kraken API error: {obj.get('error') if isinstance(obj,dict) else obj}")
    if not isinstance(obj.get("result"),dict): raise ValueError("unexpected Kraken envelope")
    return obj["result"]

def asset_matches(key,v):
    text=" ".join(str(x) for x in [key,v.get("altname"),v.get("aclass")]).upper()
    return "SOFID" in text

def pair_matches(key,v,asset_keys):
    base=str(v.get("base","")).upper(); alt=str(v.get("altname","")).upper(); ws=str(v.get("wsname","")).upper()
    base_ok=base in {x.upper() for x in asset_keys} or base=="SOFID" or alt.startswith("SOFID") or ws.startswith("SOFID/")
    quote_hint=alt.endswith(("USD","USDC","USDT")) or any(ws.endswith("/"+q) for q in ("USD","USDC","USDT"))
    return base_ok and quote_hint

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--end",default="2026-09-02"); ap.add_argument("--output",required=True); a=ap.parse_args()
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True); end=date.fromisoformat(a.end)
    status="FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"; err=None; summary={}
    try:
        au,ar=get("/Assets"); pu,pr=get("/AssetPairs")
        (out/"RAW_ASSETS.json").write_bytes(ar); (out/"RAW_ASSET_PAIRS.json").write_bytes(pr)
        assets=decode(ar); pairs=decode(pr)
        ah={k:v for k,v in assets.items() if asset_matches(k,v)}
        if not ah: raise ValueError("SOFID not present in official Kraken Assets")
        ph={k:v for k,v in pairs.items() if pair_matches(k,v,set(ah))}
        if not ph: raise ValueError("no SOFID fiat/stable spot pair present in official Kraken AssetPairs")
        # Deterministic preregistered quote preference: USD, then USDC, then USDT; lexical tiebreak.
        def rank(item):
            k,v=item; text=(str(v.get("wsname"))+' '+str(v.get("altname"))).upper()
            qr=next((i for i,q in enumerate(("USD","USDC","USDT")) if text.endswith('/'+q) or text.endswith(q)),99)
            return (qr,k)
        pair_key,pair=sorted(ph.items(),key=rank)[0]
        pair_req=pair.get("altname") or pair_key
        since=int(datetime.combine(end-timedelta(days=32),datetime.min.time(),tzinfo=timezone.utc).timestamp())
        ou,orr=get("/OHLC",{"pair":pair_req,"interval":"1440","since":str(since)})
        (out/"RAW_OHLC.json").write_bytes(orr); oo=decode(orr)
        keys=[k for k in oo if k!="last"]
        if len(keys)!=1 or not isinstance(oo[keys[0]],list): raise ValueError(f"unexpected Kraken OHLC result keys {keys}")
        rows=[]
        for x in oo[keys[0]]:
            if not isinstance(x,list) or len(x)<8: raise ValueError("Kraken OHLC schema mismatch")
            ts=int(x[0]); d=datetime.fromtimestamp(ts,timezone.utc).date()
            if d>end: continue
            op,hi,lo,cl=map(float,x[1:5]); vol=float(x[6]); count=int(x[7])
            if vol<0 or count<0: raise ValueError("negative Kraken volume/count")
            if not (lo<=min(op,cl)<=max(op,cl)<=hi): raise ValueError("OHLC invariant failed")
            rows.append({"timestamp":ts,"day":d.isoformat(),"open":op,"high":hi,"low":lo,"close":cl,"volume":vol,"trade_count":count})
        rows.sort(key=lambda x:x["timestamp"])
        if not rows: raise ValueError("no in-window Kraken OHLC rows")
        dup=len(rows)-len({x["timestamp"] for x in rows})
        monotonic=all(rows[i]["timestamp"]<rows[i+1]["timestamp"] for i in range(len(rows)-1))
        have={x["day"] for x in rows}; first=date.fromisoformat(rows[0]["day"]); last=date.fromisoformat(rows[-1]["day"])
        gaps=[]; d=first
        while d<=last:
            if d.isoformat() not in have: gaps.append(d.isoformat())
            d+=timedelta(days=1)
        qa=dup==0 and monotonic and not gaps and last<=end
        status="QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION" if qa else "FAIL_CLOSED_FULL_CORPUS_QA"
        summary={"asset_hits":ah,"pair_hits":ph,"selected_pair_key":pair_key,"selected_pair":pair,"ohlc_result_key":keys[0],"rows":len(rows),"earliest_day":rows[0]["day"],"latest_day":rows[-1]["day"],"duplicate_rows":dup,"monotonic":monotonic,"missing_days_within_returned_interval":gaps,"qa_pass":qa,"urls":{"assets":au,"pairs":pu,"ohlc":ou},"sha256":{"assets":hashlib.sha256(ar).hexdigest(),"pairs":hashlib.sha256(pr).hexdigest(),"ohlc":hashlib.sha256(orr).hexdigest()}}
        (out/"CANDLES.jsonl").write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in rows))
    except Exception as exc: err=str(exc)
    frozen={"schema_version":"GATE_BTC_2_V2A_SOFID_KRAKEN_PHYSICAL_V1","symbol":"SOFID","coin_id":"sofiusd","provider":"KRAKEN","market":"SPOT","status":status,"requested_end_utc":a.end,"error":err,"research_only":True,"shadow_only":True,"not_approved":True,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_counter_reset":True,"no_silent_source_substitution":True,"fail_closed":True,"qualification_only":True,"source_admitted":False,"scientific_credit":False,"prospective_credit":False,"d0_credit":0,"admission_scope":"NONE",**summary}
    (out/"SUMMARY.json").write_text(json.dumps(frozen,indent=2,sort_keys=True)+"\n")
    print(json.dumps(frozen,indent=2,sort_keys=True)); return 0 if frozen.get("qa_pass") else 2
if __name__=="__main__": raise SystemExit(main())
