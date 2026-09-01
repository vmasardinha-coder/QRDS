#!/usr/bin/env python3
"""Full physical QA of preregistered Bybit MNTUSDT public daily archive.
Qualification/readiness only: never backfill PIT, grant scientific/prospective credit, or feed execution.
"""
from __future__ import annotations
import argparse,csv,gzip,hashlib,json,re,time,urllib.request
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import date,datetime,timedelta,timezone
from pathlib import Path

BASE="https://public.bybit.com/spot/MNTUSDT/"
PAIR="MNTUSDT"
DAY_RE=re.compile(r'href=["\'](MNTUSDT_(\d{4}-\d{2}-\d{2})\.csv\.gz)["\']')
EXPECTED_HEADER=["id","timestamp","price","volume","side"]


def request_bytes(url,retries=3):
    last=None
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={"Accept":"*/*","User-Agent":"QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req,timeout=60) as r:return r.read()
        except Exception as e:
            last=e; time.sleep(2**i)
    raise RuntimeError(f"source request failed: {last}")


def parse_day(name,day_text,raw):
    digest=hashlib.sha256(raw).hexdigest()
    text=gzip.decompress(raw).decode("utf-8-sig")
    reader=csv.DictReader(text.splitlines())
    if reader.fieldnames!=EXPECTED_HEADER: raise ValueError(f"schema mismatch {reader.fieldnames}")
    rows=0; first_key=None; last_key=None; prev_key=None; monotonic=True; prices=[]; volume=0.0
    for row in reader:
        k=(int(float(row["timestamp"])),int(row["id"]))
        if prev_key is not None and k<prev_key: monotonic=False
        prev_key=k; first_key=first_key or k; last_key=k
        p=float(row["price"]); v=float(row["volume"])
        if v<0: raise ValueError("negative volume")
        prices.append(p); volume+=v; rows+=1
    if not rows: raise ValueError("empty archive object")
    observed=datetime.fromtimestamp(first_key[0]/1000,timezone.utc).date().isoformat()
    last_observed=datetime.fromtimestamp(last_key[0]/1000,timezone.utc).date().isoformat()
    if observed!=day_text or last_observed!=day_text: raise ValueError(f"trade UTC day spill {observed}..{last_observed}")
    o=prices[0]; c=prices[-1]; h=max(prices); l=min(prices)
    if not (l<=min(o,c)<=max(o,c)<=h): raise ValueError("derived OHLC invariant failed")
    return {"object":name,"day":day_text,"sha256":digest,"compressed_bytes":len(raw),"trade_rows":rows,"trade_order_monotonic":monotonic,"open":o,"high":h,"low":l,"close":c,"base_volume":volume,"qa_pass":monotonic}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",default="artifacts/gate_btc_2/v2a_mnt_full_corpus_qa"); ap.add_argument("--workers",type=int,default=6); args=ap.parse_args()
    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    listing=request_bytes(BASE); (out/"archive_listing.html").write_bytes(listing)
    listing_sha=hashlib.sha256(listing).hexdigest(); text=listing.decode("utf-8",errors="replace")
    entries=sorted({m.group(2):m.group(1) for m in DAY_RE.finditer(text)}.items())
    if not entries: raise SystemExit("no exact MNTUSDT daily objects")
    start=date.fromisoformat(entries[0][0]); end=date.fromisoformat(entries[-1][0]); expected=[]; d=start
    while d<=end: expected.append(d.isoformat()); d+=timedelta(days=1)
    listed=[d for d,_ in entries]; missing=sorted(set(expected)-set(listed)); duplicate_listing=len(listed)-len(set(listed))
    results=[]; failures=[]
    def work(item):
        day_text,name=item; raw=request_bytes(BASE+name); return parse_day(name,day_text,raw)
    with ThreadPoolExecutor(max_workers=max(1,args.workers)) as ex:
        futs={ex.submit(work,e):e for e in entries}
        for f in as_completed(futs):
            e=futs[f]
            try: results.append(f.result())
            except Exception as exc: failures.append({"day":e[0],"object":e[1],"error":str(exc)})
    results.sort(key=lambda x:x["day"]); failures.sort(key=lambda x:x["day"])
    bad_order=sum(not r["trade_order_monotonic"] for r in results)
    qa_pass=(not missing and duplicate_listing==0 and not failures and len(results)==len(expected) and bad_order==0)
    manifest={"schema_version":"GATE_BTC_2_V2A_MNT_FULL_CORPUS_QA_V1","issue":111,"provider":"Bybit","market":"SPOT","pair":PAIR,"coin_id":"mantle","symbol":"MNT","qualification_only":True,"research_only":True,"shadow_only":True,"not_approved":True,"dataset_sealed":False,"scientific_credit":False,"prospective_credit":False,"promotion_allowed":False,"engine_feed":False,"orders":0,"real_capital_brl":0,"no_retune":True,"no_backfill":True,"no_silent_source_substitution":True,"fail_closed":True,"listing_sha256":listing_sha,"earliest_day":entries[0][0],"latest_day":entries[-1][0],"listed_objects":len(entries),"expected_calendar_days":len(expected),"missing_listing_days":missing,"duplicate_listing_days":duplicate_listing,"physical_objects_ok":len(results),"physical_object_failures":failures,"bad_trade_order_objects":bad_order,"qa_pass":qa_pass,"source_qualification_outcome":"ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if qa_pass else "FAIL_CLOSED_FULL_CORPUS_QA","admission_scope":"NONE","retroactive_v2a_repair_allowed":False,"object_results_file":"OBJECT_RESULTS.jsonl"}
    (out/"OBJECT_RESULTS.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in results),encoding="utf-8")
    (out/"SUMMARY.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(manifest,indent=2,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
