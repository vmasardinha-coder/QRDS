#!/usr/bin/env python3
from __future__ import annotations
import gzip, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, timedelta
from pathlib import Path

SYMBOLS=("AAPL","MSFT","NVDA","META","AMZN")
UA={
    "User-Agent":"QRDS-research-only/1.0 research@example.invalid",
    "Accept":"application/json,text/plain,*/*",
    "Accept-Language":"en-US,en;q=0.9",
}
SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_BACKFILL":True,"NO_LATE_SEAL":True,"NO_COUNTER_RESET":True,"NO_RETUNE":True,"FAIL_CLOSED":True}

def decode_json(raw:bytes):
    if raw[:2]==b'\x1f\x8b':
        raw=gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))

def get_json(url:str, headers:dict|None=None):
    req=urllib.request.Request(url,headers=headers or UA)
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=r.read()
    return raw,decode_json(raw)

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def parse_sec_tickers(obj):
    out={}
    for row in obj.values():
        ticker=str(row.get("ticker","")).upper()
        if ticker:
            out[ticker]={"cik":int(row["cik_str"]),"title":row.get("title")}
    return out

def parse_nasdaq_rows(obj):
    data=(obj or {}).get("data") or {}
    trades=(data.get("tradesTable") or {}).get("rows") or []
    clean=[]
    for r in trades:
        if not r.get("date") or not r.get("close") or r.get("volume") in (None,""):
            continue
        clean.append({k:r.get(k) for k in ("date","close","volume","open","high","low")})
    return clean

def probe(today:date|None=None):
    today=today or date.today(); start=today-timedelta(days=45)
    result={"schema":"qrds.factory.us_mega_tech_data_probe.v1","frontier":"US_MEGA_TECH_UNIVARIATE","symbols":list(SYMBOLS),"source_stage":"DATA_ONLY","scientific_credit":0,"economics_allowed":False,"safety":SAFETY,"identity":{},"history":{},"blockers":["CORPORATE_ACTION_TREATMENT_NOT_QUALIFIED","PIT_UNIVERSE_NOT_QUALIFIED"]}
    try:
        raw,obj=get_json("https://www.sec.gov/files/company_tickers.json",{"User-Agent":"QRDS research contact research@example.invalid","Accept":"application/json","Host":"www.sec.gov"})
        tickers=parse_sec_tickers(obj); result["sec_raw_sha256"]=sha(raw)
        for s in SYMBOLS:
            if s in tickers: result["identity"][s]=tickers[s]
    except Exception as e:
        result["sec_error"]=type(e).__name__+":"+str(e)
    for s in SYMBOLS:
        params=urllib.parse.urlencode({"assetclass":"stocks","fromdate":start.strftime("%m/%d/%Y"),"todate":today.strftime("%m/%d/%Y"),"limit":"500"})
        url=f"https://api.nasdaq.com/api/quote/{s}/historical?{params}"
        try:
            raw,obj=get_json(url); rows=parse_nasdaq_rows(obj)
            result["history"][s]={"row_count":len(rows),"raw_sha256":sha(raw),"first_date":rows[-1]["date"] if rows else None,"last_date":rows[0]["date"] if rows else None}
        except Exception as e:
            result["history"][s]={"row_count":0,"error":type(e).__name__+":"+str(e)}
        time.sleep(0.2)
    identity_ok=all(s in result["identity"] for s in SYMBOLS)
    history_ok=all(result["history"].get(s,{}).get("row_count",0)>=5 for s in SYMBOLS)
    result["identity_gate"]="PASS" if identity_ok else "FAIL_CLOSED"
    result["historical_availability_gate"]="PASS" if history_ok else "FAIL_CLOSED"
    result["status"]="SOURCE_CANDIDATE_PARTIAL" if identity_ok and history_ok else "DATA_GAP_FAIL_CLOSED"
    result["data_green"]=False
    return result

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);a=ap.parse_args()
    r=probe();p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":r["status"],"identity_gate":r["identity_gate"],"historical_availability_gate":r["historical_availability_gate"],"data_green":False,"orders":0,"real_capital":0},sort_keys=True))
if __name__=="__main__":main()
