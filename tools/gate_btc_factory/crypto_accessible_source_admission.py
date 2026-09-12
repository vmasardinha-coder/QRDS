#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

REQ={(v,a,m) for v,a,m in [
("OKX","BTC","SPOT"),("OKX","BTC","PERPETUAL"),("OKX","BTC","FUNDING"),("COINBASE","BTC","SPOT"),
("OKX","ETH","SPOT"),("OKX","ETH","PERPETUAL"),("OKX","ETH","FUNDING"),("COINBASE","ETH","SPOT")
]}
def packet_info(x):
    got={(r.get("venue"),r.get("asset"),r.get("market")) for r in x.get("records",[])}
    if not REQ.issubset(got): return False,None
    try:
        r=next(r for r in x["records"] if (r.get("venue"),r.get("asset"),r.get("market"))==("OKX","BTC","SPOT"))
        bucket=int(r["bar"]["start_ms"])
        # all completed bar records must identify the same 5m bucket
        for q in x["records"]:
            if q.get("market") in ("SPOT","PERPETUAL"):
                b=q.get("bar",{})
                s=int(b["start_ms"]) if "start_ms" in b else int(b["start_s"])*1000
                if s!=bucket:return False,None
        return True,bucket
    except Exception:return False,None

def evaluate(audit_dir:Path, previous:Path|None=None, required=3):
    by_bucket={}
    for p in audit_dir.glob("*.json"):
        try:x=json.loads(p.read_text(encoding="utf-8"))
        except Exception:continue
        ts=x.get("captured_at_utc");ok,bucket=packet_info(x)
        if not ts or not ok or bucket is None:continue
        # first immutable observation per completed bucket wins
        if bucket not in by_bucket or ts<by_bucket[bucket][0]:
            by_bucket[bucket]=(ts,p.name,x.get("packet_sha256"))
    buckets=sorted(by_bucket)
    streak=[]
    for b in reversed(buckets):
        if not streak or streak[-1]-b==300000:streak.append(b)
        else:break
    streak=list(reversed(streak))
    prev={}
    if previous and previous.exists():
        try:prev=json.loads(previous.read_text(encoding="utf-8"))
        except Exception:prev={}
    admitted_before=bool(prev.get("source_admitted_forward_only"))
    admitted=admitted_before or len(streak)>=required
    admitted_at=prev.get("admitted_at_utc"); admitted_by=prev.get("admitted_by_packet"); admitted_bucket=prev.get("admitted_bucket_start_ms")
    if admitted and not admitted_at and len(streak)>=required:
        b=streak[required-1] if len(streak)==required else streak[-1]
        admitted_at,admitted_by,_=by_bucket[b]; admitted_bucket=b
    return {
      "schema":"qrds.factory.crypto_accessible_source_admission.v1","frontier":"CRYPTO_ACCESSIBLE_FORWARD_V1",
      "required_complete_consecutive_buckets":required,"observed_unique_complete_bucket_count":len(buckets),
      "complete_consecutive_bucket_streak":len(streak),"latest_complete_bucket_start_ms":buckets[-1] if buckets else None,
      "source_admitted_forward_only":admitted,"admitted_at_utc":admitted_at,"admitted_by_packet":admitted_by,"admitted_bucket_start_ms":admitted_bucket,
      "family_state":"SOURCE_ADMITTED_PENDING_PREREG_ACTIVATION" if admitted else "WAITING_SOURCE",
      "historical_backfill_credit":0,"economics_read":False,"promotion_allowed":False,"orders":0,"real_capital":0
    }
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",required=True);ap.add_argument("--out",required=True);ap.add_argument("--previous")
    a=ap.parse_args();outp=Path(a.out);prev=Path(a.previous) if a.previous else outp
    x=evaluate(Path(a.audit_dir),prev);outp.parent.mkdir(parents=True,exist_ok=True);outp.write_text(json.dumps(x,indent=2)+"\n");print(json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
