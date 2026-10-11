#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,math
from datetime import datetime,timezone
from pathlib import Path

REQUIRED={(v,a,m) for v in ("BINANCE","OKX") for a in ("BTC","ETH") for m in ("SPOT","PERPETUAL","FUNDING")}|{("COINBASE",a,"SPOT") for a in ("BTC","ETH")}

def packet_evidence(x):
    try:
        if x.get("status")!="COMPLETE_PROSPECTIVE_PACKET" or x.get("record_count")!=14 or x.get("required_record_count")!=14 or x.get("errors"):
            return False,None,"INCOMPLETE_PACKET"
        if x.get("schema")!="qrds.factory.crypto_forward_capture.v1" or x.get("scientific_credit")!=0 or x.get("historical_backfill_credit")!=0 or x.get("economics_feedback_allowed") is not False:
            return False,None,"PACKET_AUTHORITY_MISMATCH"
        records=x["records"]
        roles=[(r.get("venue"),r.get("asset"),r.get("market")) for r in records]
        if len(records)!=14 or set(roles)!=REQUIRED or len(set(roles))!=14:
            return False,None,"REQUIRED_ROLES_MISMATCH"
        actual=hashlib.sha256(json.dumps({k:v for k,v in x.items() if k!="packet_sha256"},sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if actual!=x.get("packet_sha256"):return False,None,"PACKET_HASH_MISMATCH"
        safety=x["safety"]
        if safety.get("ORDERS")!=0 or safety.get("REAL_CAPITAL")!=0 or safety.get("ENGINE_FEED") is not False or any(safety.get(k) is not True for k in ("RESEARCH_ONLY","SHADOW_ONLY","NOT_APPROVED")):
            return False,None,"SAFETY_MISMATCH"
        captured=datetime.fromisoformat(x["captured_at_utc"].replace("Z","+00:00"))
        if captured.tzinfo is None:return False,None,"CAPTURE_TIME_NOT_UTC_AWARE"
        if captured>datetime.now(timezone.utc):return False,None,"CAPTURE_TIME_IN_FUTURE"
        starts=[]
        for record in records:
            venue,asset,market=record["venue"],record["asset"],record["market"]
            expected_symbol=(asset+"USDT" if venue=="BINANCE" else asset+"-USD" if venue=="COINBASE" else asset+"-USDT"+("-SWAP" if market in ("PERPETUAL","FUNDING") else ""))
            if record.get("symbol")!=expected_symbol:return False,None,"INSTRUMENT_IDENTITY_MISMATCH"
            raw_hash=record.get("raw_sha256","")
            if len(raw_hash)!=64 or any(c not in "0123456789abcdef" for c in raw_hash):return False,None,"RAW_HASH_MISSING"
            if record["market"]=="FUNDING":
                if not math.isfinite(float(record["funding_rate"])):return False,None,"FUNDING_MISSING"
                continue
            bar=record["bar"]
            o,h,l,c,v=(float(bar[k]) for k in ("open","high","low","close","volume"))
            if not all(math.isfinite(n) for n in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or l>min(o,c) or h<max(o,c):
                return False,None,"INVALID_OHLCV"
            start=int(bar["start_ms"]) if "start_ms" in bar else int(bar["start_s"])*1000
            if start%300000:return False,None,"INVALID_BUCKET"
            starts.append(start)
        if len(set(starts))!=1:return False,None,"BAR_BUCKET_MISMATCH"
        bucket=starts[0]
        if captured.astimezone(timezone.utc).timestamp()*1000 < bucket+300000+120000:
            return False,bucket,"FROZEN_CAPTURE_DELAY_NOT_MET"
        return True,bucket,"QUALIFIED_PACKET"
    except (KeyError,TypeError,ValueError,OverflowError,AttributeError):return False,None,"INVALID_PACKET_SCHEMA"

def evaluate(audit_dir:Path, required=3):
    if required!=3:raise ValueError("frozen required packet count must remain 3")
    files=sorted(audit_dir.glob("*.json"), key=lambda p:p.name)
    packets=[]
    for p in files:
        try:x=json.loads(p.read_text())
        except Exception:
            packets.append({"file":p.name,"status":None,"qualified":False,"bucket":None,"reason":"UNREADABLE_PACKET","captured_at_utc":None});continue
        ok,bucket,reason=packet_evidence(x)
        packets.append({"file":p.name,"status":x.get("status"),"packet_sha256":x.get("packet_sha256"),"qualified":ok,"bucket":bucket,"reason":reason,"captured_at_utc":x.get("captured_at_utc")})
    # Names are transport identifiers; actual capture time controls continuity.
    def capture_time(x):
        try:
            value=datetime.fromisoformat(x["captured_at_utc"].replace("Z","+00:00"))
            return value.timestamp() if value.tzinfo else float("-inf")
        except (KeyError,TypeError,ValueError,AttributeError):return float("-inf")
    packets.sort(key=capture_time)
    streak=0
    seen=set()
    previous_bucket=None
    for x in reversed(packets):
        if not x["qualified"]:break
        if x["bucket"] in seen:continue
        if previous_bucket is not None and previous_bucket-x["bucket"]!=300000:break
        seen.add(x["bucket"]);previous_bucket=x["bucket"];streak+=1
    admitted=streak>=required and all(capture_time(x)!=float("-inf") for x in packets)
    return {
      "schema":"qrds.factory.crypto_forward_source_admission.v1",
      "required_complete_consecutive_packets":required,
      "observed_packet_count":len(packets),
      "complete_consecutive_streak":streak,
      "complete_streak_counts_unique_5m_buckets":True,
      "frozen_capture_delay_seconds":120,
      "latest_packet_qualification":packets[-1]["reason"] if packets else "NO_PACKETS",
      "source_admitted_forward_only":admitted,
      "family_state":"READY_FORWARD" if admitted else "WAITING_SOURCE",
      "historical_backfill_credit":0,
      "economics_read":False,
      "promotion_allowed":False,
      "orders":0,
      "real_capital":0
    }
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    x=evaluate(Path(a.audit_dir));q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(x,indent=2)+"\n");print(json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
