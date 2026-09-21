#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
FIDS=["COKBF01","COKBF02","COKBF03","COKBF04","COCV01","COCV02","COCV03","COCV04"]
def fnum(x): return float(x)
def sign(x): return 1 if x>0 else (-1 if x<0 else 0)
def key(r): return (r.get("venue"),r.get("asset"),r.get("market"))
def bars(packet,asset):
    d={key(r):r for r in packet["records"]}
    return {
      "os":d[("OKX",asset,"SPOT")]["bar"],
      "op":d[("OKX",asset,"PERPETUAL")]["bar"],
      "of":d[("OKX",asset,"FUNDING")],
      "cs":d[("COINBASE",asset,"SPOT")]["bar"]
    }
def start_ms(b): return int(b.get("start_ms",int(b.get("start_s",0))*1000))
def ret(b): return fnum(b["close"])/fnum(b["open"])-1
def observations(p0,p1):
    out=[]
    for asset in ("BTC","ETH"):
        a=bars(p0,asset);b=bars(p1,asset)
        t=start_ms(a["os"]);t1=start_ms(b["os"])
        if t1-t!=300000:continue
        if any(start_ms(a[x])!=t for x in ("op","cs")):continue
        if any(start_ms(b[x])!=t1 for x in ("op","cs")):continue
        basis=fnum(a["op"]["close"])/fnum(a["os"]["close"])-1
        funding=fnum(a["of"]["funding_rate"])
        okr=ret(a["os"]); cbr=ret(a["cs"]); dis=fnum(a["os"]["close"])/fnum(a["cs"]["close"])-1
        next_ok=ret(b["os"]); next_cb=ret(b["cs"]); next_rel=ret(b["op"])-next_ok; next_spot_rel=next_ok-next_cb
        specs=[
          ("COKBF01",sign(basis),next_rel,20),("COKBF02",-sign(basis),next_rel,20),
          ("COKBF03",sign(funding),next_rel,20),("COKBF04",-sign(funding),next_rel,20),
          ("COCV01",sign(okr),next_cb,10),("COCV02",sign(cbr),next_ok,10),
          ("COCV03",-sign(dis),next_spot_rel,20),("COCV04",sign(dis),next_spot_rel,20)]
        for fid,sig,gross,cost in specs:
            if sig:
                out.append({"family_id":fid,"asset":asset,"signal_bucket_start_ms":t,"outcome_bucket_start_ms":t1,
                  "signal":sig,"gross_return":sig*gross,"net_return_primary":sig*gross-cost/10000.0})
    return out
def sealed_pairs(audit_dir,eligible_start):
    groups={}
    ignored_legacy=0
    for p in Path(audit_dir).glob("*.json"):
        try:x=json.loads(p.read_text())
        except Exception:continue
        if not x.get("captured_at_utc") or x["captured_at_utc"]<eligible_start:continue
        pair=x.get("prospective_pair")
        if not isinstance(pair,dict):ignored_legacy+=1;continue
        if pair.get("retroactive_pairing_allowed") is not False or pair.get("exact_next_bucket_required") is not True:continue
        pid=pair.get("pair_id");role=pair.get("role")
        if not pid or role not in ("SIGNAL_T","OUTCOME_T_PLUS_1"):continue
        groups.setdefault(pid,{})[role]=x
    pairs=[]
    for pid,g in groups.items():
        if set(g)!={"SIGNAL_T","OUTCOME_T_PLUS_1"}:continue
        p0,p1=g["SIGNAL_T"],g["OUTCOME_T_PLUS_1"]
        meta0,meta1=p0["prospective_pair"],p1["prospective_pair"]
        if meta0.get("signal_bucket_start_ms")!=meta1.get("signal_bucket_start_ms"):continue
        pairs.append((meta0["signal_bucket_start_ms"],pid,p0,p1))
    pairs.sort(key=lambda z:(z[0],z[1]))
    return pairs,ignored_legacy
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",required=True);ap.add_argument("--admission",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    adm=json.loads(Path(a.admission).read_text())
    ledger={"schema":"qrds.factory.crypto_accessible_blind_ledger.v2","frontier":"CRYPTO_ACCESSIBLE_FORWARD_V1","source_admitted":adm.get("source_admitted_forward_only",False),"admitted_at_utc":adm.get("admitted_at_utc"),"observations":[],"checkpoint_economics":{},"partial_aggregate_economics_visible":False,"prospective_pair_protocol_required":True,"legacy_snapshot_retroactive_pairing_allowed":False,"orders":0,"real_capital":0}
    if not ledger["source_admitted"]:
        Path(a.out).write_text(json.dumps(ledger,indent=2)+"\n");print(json.dumps({"status":"WAITING_SOURCE","observations":0}));return
    activation="2026-09-14T00:00:00Z"
    eligible_start=max(adm["admitted_at_utc"],activation)
    ledger["activation_not_before_utc"]=activation
    ledger["evaluation_start_not_before_utc"]=eligible_start
    pairs,ignored_legacy=sealed_pairs(a.audit_dir,eligible_start)
    ledger["sealed_pair_count"]=len(pairs);ledger["ignored_legacy_snapshot_count"]=ignored_legacy
    seen=set()
    for _,pid,p0,p1 in pairs:
        for o in observations(p0,p1):
            k=(o["family_id"],o["asset"],o["signal_bucket_start_ms"])
            if k not in seen:
                seen.add(k);o["prospective_pair_id"]=pid;ledger["observations"].append(o)
    counts={fid:sum(o["family_id"]==fid for o in ledger["observations"]) for fid in FIDS}
    ledger["observation_counts"]=counts
    # Aggregate economics deliberately withheld until exact 60-observation checkpoint.
    for fid,n in counts.items():
        if n>=60 and n%60==0:
            xs=[o["net_return_primary"] for o in ledger["observations"] if o["family_id"]==fid]
            mean=sum(xs)/len(xs)
            sd=(sum((x-mean)**2 for x in xs)/(len(xs)-1))**0.5 if len(xs)>1 else 0
            ledger["checkpoint_economics"][fid]={"checkpoint":n,"mean_net":mean,"annualized_sharpe_equiv":mean/sd*math.sqrt(365*24*12) if sd else 0}
    Path(a.out).write_text(json.dumps(ledger,indent=2)+"\n");print(json.dumps({"status":"ACTIVE_BLIND" if pairs else "WAITING_SEALED_PROSPECTIVE_PAIR","sealed_pairs":len(pairs),"ignored_legacy":ignored_legacy,"observations":len(ledger["observations"]),"counts":counts,"checkpoints":list(ledger["checkpoint_economics"])}))
if __name__=="__main__":main()
