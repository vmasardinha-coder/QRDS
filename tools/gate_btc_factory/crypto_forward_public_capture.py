#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,time,urllib.parse,urllib.request,uuid
from datetime import datetime,timezone
from pathlib import Path
UA={"User-Agent":"QRDS-research-only/1.0"}
ACCESSIBLE_REQUIRED={("OKX",a,m) for a in ("BTC","ETH") for m in ("SPOT","PERPETUAL","FUNDING")}|{("COINBASE",a,"SPOT") for a in ("BTC","ETH")}
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
def accessible_bucket_start_ms(packet):
    d={(r.get("venue"),r.get("asset"),r.get("market")):r for r in packet.get("records",[])}
    if not ACCESSIBLE_REQUIRED.issubset(d): raise RuntimeError("ACCESSIBLE_PACKET_INCOMPLETE_FAIL_CLOSED")
    starts=[]
    for asset in ("BTC","ETH"):
        for venue,market in (("OKX","SPOT"),("OKX","PERPETUAL"),("COINBASE","SPOT")):
            b=d[(venue,asset,market)]["bar"]
            starts.append(int(b.get("start_ms",int(b.get("start_s",0))*1000)))
    if len(set(starts))!=1: raise RuntimeError("ACCESSIBLE_PACKET_BUCKET_MISMATCH_FAIL_CLOSED")
    return starts[0]
def stamp_pair(packet,pair_id,role,signal_bucket_start_ms):
    packet["prospective_pair"]={"pair_id":pair_id,"role":role,"signal_bucket_start_ms":signal_bucket_start_ms,"exact_next_bucket_required":True,"retroactive_pairing_allowed":False}
    packet["packet_sha256"]=hashlib.sha256(json.dumps({k:v for k,v in packet.items() if k!="packet_sha256"},sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return packet
def capture_prospective_pair(capture_fn=capture,sleep_fn=time.sleep,max_wait_seconds=420,poll_seconds=15):
    pair_id=str(uuid.uuid4())
    p0=capture_fn(); t0=accessible_bucket_start_ms(p0)
    # p0 is the latest completed bucket; its exact next 5m bucket is still unseen as a completed outcome.
    stamp_pair(p0,pair_id,"SIGNAL_T",t0)
    deadline=time.monotonic()+max_wait_seconds
    while time.monotonic()<deadline:
        sleep_fn(poll_seconds)
        p1=capture_fn()
        try:t1=accessible_bucket_start_ms(p1)
        except RuntimeError:continue
        if t1==t0:continue
        if t1==t0+300000:
            stamp_pair(p1,pair_id,"OUTCOME_T_PLUS_1",t0)
            return p0,p1
        if t1>t0+300000: raise RuntimeError("EXACT_NEXT_BUCKET_MISSED_FAIL_CLOSED")
    raise RuntimeError("EXACT_NEXT_BUCKET_TIMEOUT_FAIL_CLOSED")
def write_packet(path,packet):
    q=Path(path);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(packet,indent=2)+"\n")
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out");ap.add_argument("--pair-dir");ap.add_argument("--max-wait-seconds",type=int,default=420);ap.add_argument("--poll-seconds",type=int,default=15);a=ap.parse_args()
    if bool(a.out)==bool(a.pair_dir): raise SystemExit("exactly one of --out or --pair-dir is required")
    if a.pair_dir:
        p0,p1=capture_prospective_pair(max_wait_seconds=a.max_wait_seconds,poll_seconds=a.poll_seconds)
        root=Path(a.pair_dir);write_packet(root/"T.json",p0);write_packet(root/"T_PLUS_1.json",p1)
        print(json.dumps({"status":"COMPLETE_PROSPECTIVE_PAIR","pair_id":p0["prospective_pair"]["pair_id"],"t":accessible_bucket_start_ms(p0),"t1":accessible_bucket_start_ms(p1),"orders":0,"real_capital":0},sort_keys=True));return
    p=capture();write_packet(a.out,p);print(json.dumps({"status":p["status"],"records":p["record_count"],"errors":len(p["errors"]),"orders":0,"real_capital":0},sort_keys=True))
if __name__=="__main__":main()
