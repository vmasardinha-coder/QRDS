#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
ORIGINAL=["CRBF01","CRBF02","CRBF03","CRBF04","CRCV01","CRCV02","CRCV03","CRCV04"]
ACCESS=["COKBF01","COKBF02","COKBF03","COKBF04","COCV01","COCV02","COCV03","COCV04"]
def build(original_adm, accessible_adm):
    oa=bool(original_adm.get("source_admitted_forward_only"))
    aa=bool(accessible_adm.get("source_admitted_forward_only"))
    fam=[]
    fam += [{"id":x,"generation":"ORIGINAL_MULTI_VENUE","state":"READY_FORWARD" if oa else "WAITING_SOURCE"} for x in ORIGINAL]
    fam += [{"id":x,"generation":"ACCESSIBLE_OKX_COINBASE","state":"READY_FORWARD" if aa else "WAITING_SOURCE"} for x in ACCESS]
    return {"schema":"qrds.factory.crypto_family_state_runtime.v1","family_count":16,"families":fam,
      "counts":{"READY_FORWARD":sum(x["state"]=="READY_FORWARD" for x in fam),"WAITING_SOURCE":sum(x["state"]=="WAITING_SOURCE" for x in fam)},
      "economics_read":False,"scientific_credit":0,"promotion_allowed":False}
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--original-admission",required=True);ap.add_argument("--accessible-admission",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    o=json.loads(Path(a.original_admission).read_text());q=json.loads(Path(a.accessible_admission).read_text());x=build(o,q);Path(a.out).write_text(json.dumps(x,indent=2)+"\n");print(json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
