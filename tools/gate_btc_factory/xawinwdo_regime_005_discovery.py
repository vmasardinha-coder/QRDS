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
  # Frozen semantics: every scored observation uses 20/80 thresholds estimated
  # strictly from observations prior to that scored observation.
  z=[]
  for k,(x,y) in enumerate(zip(a,b)):
   if k<5: continue
   aa=sorted(a[:k]);bb=sorted(b[:k]);ix=lambda q,p:q[int(p*(len(q)-1))]
   al,ah,bl,bh=ix(aa,.2),ix(aa,.8),ix(bb,.2),ix(bb,.8)
   z.append(1. if ((x<=al and y<=bl) or (x>=ah and y>=bh)) else -1. if ((x<=al and y>=bh) or (x>=ah and y<=bl)) else 0.)
  return mean(z) if z else None
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
def aligned_metric(rows,horizon,w,lag,metric,target):
 s=series(rows,horizon); out=[]
 target_root=0 if target.endswith("_WIN") else 1
 for i in range(w-1,len(s)-1):
  # Frozen sign convention: negative lag => feature precedes target;
  # zero => contemporaneous feature to forward target; positive => target clock precedes feature.
  ti=i+1-lag
  if not (0<=ti<len(s)): continue
  hist=s[i-w+1:i+1]; targ=[]; feat=[]
  for j,z in enumerate(hist):
   gi=i-w+1+j; tj=gi+1-lag
   if 0<=tj<len(s):
    feat.append(z[1-target_root]); targ.append(s[tj][target_root])
  if len(feat)<3: continue
  v=dep(metric,feat,targ)
  if v is not None: out.append(v)
 return out

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--splits",required=True);ap.add_argument("--rule",required=True);ap.add_argument("--semantics",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 m=json.loads(Path(a.splits).read_text());rule=json.loads(Path(a.rule).read_text());sem=json.loads(Path(a.semantics).read_text())
 assert m["family_id"]==rule["family_id"]==sem["family_id"]==FAMILY and m["next_stage"]=="DISCOVERY_ONLY_VALIDATION_HOLDOUT_SEALED"
 rows=m["splits"]["discovery"]
 targets=["next_bar_WIN","next_bar_WDO","next_session_WIN","next_session_WDO"]; horizons=["intraday_bar","1_session","5_sessions","20_sessions","60_sessions"]; windows=[20,60]; lags=[-12,-6,-3,-1,0,1,3,6,12]; metrics=["Pearson","Spearman","sign_concordance","tail_quadrant_frequency"];cand=[]
 for h in horizons:
  for w in windows:
   for lag in lags:
    for met in metrics:
     for target in targets:
      x=aligned_metric(rows,h,w,lag,met,target)
      if len(x)>1 and sd(x)>0:
       score=mean(x)/sd(x);cand.append({"target":target,"horizon":h,"rolling_window":w,"lead_lag":lag,"metric":met,"discovery_metric":mean(x),"standardized_metric":score,"sign":1 if mean(x)>0 else -1 if mean(x)<0 else 0,"n":len(x)})
 def lagkey(x):return (abs(x),0 if x<0 else 1 if x==0 else 2)
 cand.sort(key=lambda x:(-abs(x["standardized_metric"]),x["rolling_window"],lagkey(x["lead_lag"]),x["target"],x["horizon"],x["metric"]))
 assert cand
 c=cand[0];out={"schema":"qrds.factory.xawinwdo_regime_005.candidate_freeze.v1","family_id":FAMILY,"status":"CANDIDATE_FROZEN_BEFORE_VALIDATION","candidate":c,"eligible_computable_candidates":len(cand),"discovery_only":True,"validation_read":False,"holdout_read":False,"splits_sha256":sha(a.splits),"rule_sha256":sha(a.rule),"semantics_sha256":sha(a.semantics),"safety":SAFETY,"next_stage":"VALIDATION_SINGLE_FROZEN_CANDIDATE_ALLOWED"}
 q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()
