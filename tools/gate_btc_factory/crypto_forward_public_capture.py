#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
UA={"User-Agent":"QRDS-research-only/1.0"}
def raw_get(url,params=None):
    if params:url=url+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r: raw=r.read()
    return raw,json.loads(raw.decode("utf-8"))
def h(b): return hashlib.sha256(b).hexdigest()
def completed_cutoff(): return int(time.time()//300*300)-300
def pick_binance(rows):
    cut=completed_cutoff()*1000; good=[r for r in rows if int(r[0])<=cut]
    if not good: raise RuntimeError("BINANCE_NO_COMPLETED_5M")
    r=good[-1]; return {"start_ms":int(r[0]),"open":r[1],"high":r[2],"low":r[3],"close":r[4],"volume":r[5],"close_ms":int(r[6])}
def pick_okx(obj):
    cut=completed_cutoff()*1000; rows=obj.get("data",[]); good=[r for r in rows if int(r[0])<=cut and (len(r)<9 or str(r[8])=="1")]
    if not good: raise RuntimeError("OKX_NO_COMPLETED_5M")
    r=sorted(good,key=lambda x:int(x[0]))[-1]; return {"start_ms":int(r[0]),"open":r[1],"high":r[2],"low":r[3],"close":r[4],"volume":r[5]}
def pick_coinbase(rows):
    cut=completed_cutoff(); good=[r for r in rows if int(r[0])<=cut]
    if not good: raise RuntimeError("COINBASE_NO_COMPLETED_5M")
    r=sorted(good,key=lambda x:int(x[0]))[-1]; return {"start_s":int(r[0]),"low":str(r[1]),"high":str(r[2]),"open":str(r[3]),"close":str(r[4]),"volume":str(r[5])}
def capture():
    p={"schema":"qrds.factory.crypto_forward_capture.v1","captured_at_utc":datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),"frontier":"CRYPTO_FORWARD_UNSEEN_V1","scientific_credit":0,"historical_backfill_credit":0,"economics_feedback_allowed":False,"records":[],"errors":[],"safety":{"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"FAIL_CLOSED":True}}
    for asset in ("BTC","ETH"):
      bs=asset+"USDT"
      for market,url in (("SPOT","https://api.binance.com/api/v3/klines"),("PERPETUAL","https://fapi.binance.com/fapi/v1/klines")):
        try:
          raw,obj=raw_get(url,{"symbol":bs,"interval":"5m","limit":3});p["records"].append({"venue":"BINANCE","asset":asset,"market":market,"symbol":bs,"bar":pick_binance(obj),"raw_sha256":h(raw)})
        except Exception as e:p["errors"].append({"venue":"BINANCE","asset":asset,"market":market,"error":type(e).__name__+":"+str(e)})
      try:
        raw,obj=raw_get("https://fapi.binance.com/fapi/v1/premiumIndex",{"symbol":bs});p["records"].append({"venue":"BINANCE","asset":asset,"market":"FUNDING","symbol":bs,"funding_rate":obj.get("lastFundingRate"),"next_funding_time":obj.get("nextFundingTime"),"exchange_time":obj.get("time"),"raw_sha256":h(raw)})
      except Exception as e:p["errors"].append({"venue":"BINANCE","asset":asset,"market":"FUNDING","error":type(e).__name__+":"+str(e)})
      osp=asset+"-USDT";operp=asset+"-USDT-SWAP"
      for market,symbol in (("SPOT",osp),("PERPETUAL",operp)):
        try:
          raw,obj=raw_get("https://www.okx.com/api/v5/market/candles",{"instId":symbol,"bar":"5m","limit":"3"});p["records"].append({"venue":"OKX","asset":asset,"market":market,"symbol":symbol,"bar":pick_okx(obj),"raw_sha256":h(raw)})
        except Exception as e:p["errors"].append({"venue":"OKX","asset":asset,"market":market,"error":type(e).__name__+":"+str(e)})
      try:
        raw,obj=raw_get("https://www.okx.com/api/v5/public/funding-rate",{"instId":operp});d=(obj.get("data") or [{}])[0];p["records"].append({"venue":"OKX","asset":asset,"market":"FUNDING","symbol":operp,"funding_rate":d.get("fundingRate"),"funding_time":d.get("fundingTime"),"next_funding_time":d.get("nextFundingTime"),"raw_sha256":h(raw)})
      except Exception as e:p["errors"].append({"venue":"OKX","asset":asset,"market":"FUNDING","error":type(e).__name__+":"+str(e)})
      cp=asset+"-USD"
      try:
        raw,obj=raw_get(f"https://api.exchange.coinbase.com/products/{cp}/candles",{"granularity":300});p["records"].append({"venue":"COINBASE","asset":asset,"market":"SPOT","symbol":cp,"bar":pick_coinbase(obj),"raw_sha256":h(raw)})
      except Exception as e:p["errors"].append({"venue":"COINBASE","asset":asset,"market":"SPOT","error":type(e).__name__+":"+str(e)})
    p["required_record_count"]=14;p["record_count"]=len(p["records"]);p["status"]="COMPLETE_PROSPECTIVE_PACKET" if len(p["records"])==14 and not p["errors"] else "INCOMPLETE_FAIL_CLOSED";p["packet_sha256"]=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":")).encode()).hexdigest();return p
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);a=ap.parse_args();p=capture();q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(p,indent=2)+"\n");print(json.dumps({"status":p["status"],"records":p["record_count"],"errors":len(p["errors"]),"orders":0,"real_capital":0},sort_keys=True))
if __name__=="__main__":main()
