#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
FAMILY="XAWINWDO_REGIME_005"; SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True,"H1_H31_ISOLATED":True}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mean(x):return sum(x)/len(x)
def sd(x):
 m=mean(x);return math.sqrt(sum((v-m)**2 for v in x)/(len(x)-1)) if len(x)>1 else 0
def corr(a,b):
 if len(a)<3:return None
 ma,mb=mean(a),mean(b);da=sum((x-ma)**2 for x in a);db=sum((y-mb)**2 for y in b)
 return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(da*db) if da and db else None
def ranks(x):
 o=sorted(range(len(x)),key=lambda i:x[i]);r=[0.]*len(x);i=0
 while i<len(o):
  j=i
  while j+1<len(o) and x[o[j+1]]==x[o[i]]:j+=1
  z=(i+j+2)/2
  for k in range(i,j+1):r[o[k]]=z
  i=j+1
 return r
def dep(name,a,b):
 if name=="Pearson":return corr(a,b)
 if name=="Spearman":return corr(ranks(a),ranks(b))
 if name=="sign_concordance":
  z=[1. if x*y>0 else -1. for x,y in zip(a,b) if x and y];return mean(z) if z else None
 if name=="tail_quadrant_frequency":
  if len(a)<5:return None
  aa=sorted(a[:-1]);bb=sorted(b[:-1]);ix=lambda z,p:z[int(p*(len(z)-1))]
  al,ah,bl,bh=ix(aa,.2),ix(aa,.8),ix(bb,.2),ix(bb,.8);z=[]
  for x,y in zip(a,b):z.append(1. if ((x<=al and y<=bl) or (x>=ah and y>=bh)) else -1. if ((x<=al and y>=bh) or (x>=ah and y<=bl)) else 0.)
  return mean(z)
def series(rows,horizon):
 if horizon=="intraday_bar":
  z=[]
  for day in rows:
   for b in day["bars"]:
    if b["WIN_return"] is not None and b["WDO_return"] is not None:z.append((b["WIN_return"],b["WDO_return"]))
  return z
 closes=[(r["WIN_close"],r["WDO_close"]) for r in rows if r["WIN_close"] and r["WDO_close"]]; h={"1_session":1,"5_sessions":5,"20_sessions":20,"60_sessions":60}[horizon];z=[]
 for i in range(h,len(closes)):z.append((math.log(closes[i][0]/closes[i-h][0]),math.log(closes[i][1]/closes[i-h][1])))
 return z
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--splits",required=True);ap.add_argument("--rule",required=True);ap.add_argument("--semantics",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 m=json.loads(Path(a.splits).read_text());rule=json.loads(Path(a.rule).read_text());sem=json.loads(Path(a.semantics).read_text())
 assert m["family_id"]==rule["family_id"]==sem["family_id"]==FAMILY and m["next_stage"]=="DISCOVERY_ONLY_VALIDATION_HOLDOUT_SEALED"
 rows=m["splits"]["discovery"] # validation/holdout intentionally never bound or read below
 targets=["next_bar_WIN","next_bar_WDO","next_session_WIN","next_session_WDO"]; horizons=["intraday_bar","1_session","5_sessions","20_sessions","60_sessions"]; windows=[20,60]; lags=[-12,-6,-3,-1,0,1,3,6,12]; metrics=["Pearson","Spearman","sign_concordance","tail_quadrant_frequency"];cand=[]
 for h in horizons:
  s=series(rows,h)
  for w in windows:
   for lag in lags:
    for met in metrics:
     vals=[]
     for i in range(w-1,len(s)-1):
      a0=[x[0] for x in s[i-w+1:i+1]];b0=[x[1] for x in s[i-w+1:i+1]];v=dep(met,a0,b0)
      if v is None:continue
      for target in targets:
       # Frozen target identity is retained; causal forward target availability gates score rows without using target magnitude for ranking.
       ti=i+1+lag
       if 0<=ti<len(s):vals.append((target,v))
     for target in targets:
      x=[v for t,v in vals if t==target]
      if len(x)>1 and sd(x)>0:
       score=mean(x)/sd(x);cand.append({"target":target,"horizon":h,"rolling_window":w,"lead_lag":lag,"metric":met,"discovery_metric":mean(x),"standardized_metric":score,"sign":1 if mean(x)>0 else -1 if mean(x)<0 else 0,"n":len(x)})
 def lagkey(x):return (abs(x),0 if x<0 else 1 if x==0 else 2)
 cand.sort(key=lambda x:(-abs(x["standardized_metric"]),x["rolling_window"],lagkey(x["lead_lag"]),x["target"],x["horizon"],x["metric"]))
 assert cand
 c=cand[0];out={"schema":"qrds.factory.xawinwdo_regime_005.candidate_freeze.v1","family_id":FAMILY,"status":"CANDIDATE_FROZEN_BEFORE_VALIDATION","candidate":c,"eligible_computable_candidates":len(cand),"discovery_only":True,"validation_read":False,"holdout_read":False,"splits_sha256":sha(a.splits),"rule_sha256":sha(a.rule),"semantics_sha256":sha(a.semantics),"safety":SAFETY,"next_stage":"VALIDATION_SINGLE_FROZEN_CANDIDATE_ALLOWED"}
 q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
