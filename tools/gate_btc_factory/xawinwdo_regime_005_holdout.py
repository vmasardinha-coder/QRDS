#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from xawinwdo_regime_005_discovery import series,dep
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--splits",required=True);ap.add_argument("--validation",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 m=json.loads(Path(a.splits).read_text());v=json.loads(Path(a.validation).read_text());assert v["validation_pass"] is True and v["status"]=="VALIDATION_PASS_HOLDOUT_ALLOWED"
 c=v["candidate"]; rows=m["splits"]["holdout"]; s=series(rows,c["horizon"]);w=c["rolling_window"];lag=c["lead_lag"];vals=[]
 for i in range(w-1,len(s)-1):
  ti=i+1+lag
  if not (0<=ti<len(s)):continue
  x=dep(c["metric"],[z[0] for z in s[i-w+1:i+1]],[z[1] for z in s[i-w+1:i+1]])
  if x is not None: vals.append(x)
 x=sum(vals)/len(vals) if vals else None; threshold=.5*abs(c["discovery_metric"]); same=x is not None and ((x>0)==(c["sign"]>0)); passed=x is not None and same and abs(x)>=threshold
 out={"schema":"qrds.factory.xawinwdo_regime_005.holdout.v1","family_id":"XAWINWDO_REGIME_005","candidate":c,"holdout_metric":x,"holdout_n":len(vals),"same_sign":same,"minimum_absolute_metric":threshold,"holdout_pass":passed,"status":"HISTORICAL_SURVIVOR" if passed else "REJECT_NO_RETUNE","retroactive_credit":0,"safety":v["safety"],"next_stage":"SEPARATE_BLINDED_PROSPECTIVE_ZERO_RETROACTIVE_CREDIT" if passed else "FAMILY_TERMINAL_REJECT_NO_RETUNE"}
 q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
