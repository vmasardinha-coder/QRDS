#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
from xawinwdo_regime_005_discovery import aligned_metric
FAMILY="XAWINWDO_REGIME_005"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--splits",required=True);ap.add_argument("--freeze",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 m=json.loads(Path(a.splits).read_text());f=json.loads(Path(a.freeze).read_text()); assert f["status"]=="CANDIDATE_FROZEN_BEFORE_VALIDATION" and f["holdout_read"] is False
 c=f["candidate"]; rows=m["splits"]["validation"] # holdout intentionally never bound/read
 vals=aligned_metric(rows,c["horizon"],c["rolling_window"],c["lead_lag"],c["metric"],c["target"])
 v=sum(vals)/len(vals) if vals else None; threshold=.5*abs(c["discovery_metric"]); same=v is not None and ((v>0)==(c["sign"]>0)); passed=v is not None and same and abs(v)>=threshold
 out={"schema":"qrds.factory.xawinwdo_regime_005.validation.v1","family_id":FAMILY,"candidate":c,"validation_metric":v,"validation_n":len(vals),"same_sign":same,"minimum_absolute_metric":threshold,"validation_pass":passed,"holdout_read":False,"status":"VALIDATION_PASS_HOLDOUT_ALLOWED" if passed else "REJECT_NO_RETUNE","safety":f["safety"],"next_stage":"HOLDOUT_SINGLE_FROZEN_CANDIDATE_ALLOWED" if passed else "FAMILY_TERMINAL_REJECT_NO_RETUNE"}
 q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
