#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path

FAMILY="XAWINWDO_REGIME_005"
SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True,"H1_H31_ISOLATED":True}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mean(x): return sum(x)/len(x)
def sd(x):
 m=mean(x); return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1)) if len(x)>1 else 0.0
def pearson(a,b):
 if len(a)<3:return None
 ma,mb=mean(a),mean(b); da=sum((x-ma)**2 for x in a); db=sum((y-mb)**2 for y in b)
 return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(da*db) if da>0 and db>0 else None
def ranks(x):
 o=sorted(range(len(x)),key=lambda i:x[i]); r=[0.0]*len(x); i=0
 while i<len(o):
  j=i
  while j+1<len(o) and x[o[j+1]]==x[o[i]]: j+=1
  z=(i+j+2)/2
  for k in range(i,j+1):r[o[k]]=z
  i=j+1
 return r
def metric(name,a,b):
 if name=="Pearson":return pearson(a,b)
 if name=="Spearman":return pearson(ranks(a),ranks(b))
 if name=="sign_concordance":
  z=[1.0 if x*y>0 else -1.0 for x,y in zip(a,b) if x!=0 and y!=0]; return mean(z) if z else None
 if name=="tail_quadrant_frequency":
  if len(a)<5:return None
  sa,sb=sorted(a[:-1]),sorted(b[:-1]); lo=lambda s:s[max(0,int(.2*(len(s)-1)))]; hi=lambda s:s[min(len(s)-1,int(.8*(len(s)-1)))]
  al,ah,bl,bh=lo(sa),hi(sa),lo(sb),hi(sb); z=[]
  for x,y in zip(a,b):
   if (x<=al and y<=bl) or (x>=ah and y>=bh):z.append(1.0)
   elif (x<=al and y>=bh) or (x>=ah and y<=bl):z.append(-1.0)
   else:z.append(0.0)
  return mean(z)
 raise ValueError(name)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--splits",required=True); ap.add_argument("--rule",required=True); ap.add_argument("--semantics",required=True); ap.add_argument("--out",required=True); a=ap.parse_args()
 # Deliberate sealed read: JSON is parsed, but only discovery is bound; validation/holdout are never referenced.
 m=json.loads(Path(a.splits).read_text()); rule=json.loads(Path(a.rule).read_text()); sem=json.loads(Path(a.semantics).read_text())
 assert m["family_id"]==rule["family_id"]==sem["family_id"]==FAMILY
 assert m["next_stage"]=="DISCOVERY_ONLY_VALIDATION_HOLDOUT_SEALED"
 rows=m["splits"]["discovery"]
 assert rows and rule["discovery_candidate_rule"]["candidate_count"]==1
 # Current materialization carries session-close returns. Intraday candidates require physical M5 rows and therefore fail closed
 # rather than silently shrinking the frozen candidate space or reading sealed partitions.
 required={"intraday_bar","1_session","5_sessions","20_sessions","60_sessions"}
 available={"1_session"}
 if required != available:
  out={"schema":"qrds.factory.xawinwdo_regime_005.discovery_freeze.v1","family_id":FAMILY,
       "status":"FAIL_CLOSED_DISCOVERY_INPUT_DOES_NOT_MATERIALIZE_FROZEN_CANDIDATE_SPACE",
       "reason":"MATERIALIZED_SPLITS contains session-close returns only; frozen candidate space also requires physical synchronized M5 intraday bars and 5/20/60-session horizon construction.",
       "discovery_rows_observed":len(rows),"candidate_frozen":False,"validation_read":False,"holdout_read":False,
       "splits_sha256":sha(a.splits),"rule_sha256":sha(a.rule),"semantics_sha256":sha(a.semantics),"safety":SAFETY}
  Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,sort_keys=True)); return
 raise AssertionError("unreachable until full frozen candidate space is mechanically materialized")
if __name__=="__main__": main()
