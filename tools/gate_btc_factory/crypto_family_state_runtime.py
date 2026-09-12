#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
ORIGINAL=["CRBF01","CRBF02","CRBF03","CRBF04","CRCV01","CRCV02","CRCV03","CRCV04"]
ACCESS=["COKBF01","COKBF02","COKBF03","COKBF04","COCV01","COCV02","COCV03","COCV04"]
ACTIVATION=datetime.fromisoformat("2026-09-14T00:00:00+00:00")
def state(admitted,now):
    if not admitted:return "WAITING_SOURCE"
    return "READY_FORWARD" if now>=ACTIVATION else "PREREGISTERED_WAIT_ACTIVATION"
def build(original_adm,accessible_adm,now=None):
    now=now or datetime.now(timezone.utc)
    os=state(bool(original_adm.get("source_admitted_forward_only")),now)
    aa=state(bool(accessible_adm.get("source_admitted_forward_only")),now)
    fam=[{"id":x,"generation":"ORIGINAL_MULTI_VENUE","state":os} for x in ORIGINAL]+[{"id":x,"generation":"ACCESSIBLE_OKX_COINBASE","state":aa} for x in ACCESS]
    states=sorted(set(x["state"] for x in fam))
    return {"schema":"qrds.factory.crypto_family_state_runtime.v1","family_count":16,"activation_not_before_utc":"2026-09-14T00:00:00Z","families":fam,
      "counts":{s:sum(x["state"]==s for x in fam) for s in states},"economics_read":False,"scientific_credit":0,"promotion_allowed":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--original-admission",required=True);ap.add_argument("--accessible-admission",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    o=json.loads(Path(a.original_admission).read_text());q=json.loads(Path(a.accessible_admission).read_text());x=build(o,q);Path(a.out).write_text(json.dumps(x,indent=2)+"\n");print(json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
