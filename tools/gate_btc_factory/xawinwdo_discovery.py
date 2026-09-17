#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,statistics
from datetime import datetime,timezone
from pathlib import Path
FAMILY='XAWINWDO_REGIME_001'; WINDOWS=[20,60,120,252]
def pearson(x,y):
 if len(x)<2:return None
 mx,my=statistics.fmean(x),statistics.fmean(y); a=sum((u-mx)*(v-my) for u,v in zip(x,y)); b=sum((u-mx)**2 for u in x); c=sum((v-my)**2 for v in y)
 return a/math.sqrt(b*c) if b>0 and c>0 else None
def ranks(x):
 order=sorted(range(len(x)),key=lambda i:x[i]); r=[0.0]*len(x); i=0
 while i<len(order):
  j=i
  while j+1<len(order) and x[order[j+1]]==x[order[i]]:j+=1
  v=(i+j+2)/2
  for k in range(i,j+1):r[order[k]]=v
  i=j+1
 return r
def run(path):
 m=json.loads(path.read_text()); assert m['family_id']==FAMILY and m['next_stage']=='RUN_DESCRIPTIVE_AND_DISCOVERY_ONLY'; rows=m['splits']['discovery']; results=[]
 for w in WINDOWS:
  if len(rows)<w: continue
  x=[r['WIN_return'] for r in rows[-w:]]; y=[r['WDO_return'] for r in rows[-w:]]; results.append({'window':w,'pearson':pearson(x,y),'spearman':pearson(ranks(x),ranks(y)),'sign_concordance':sum((a>=0)==(b>=0) for a,b in zip(x,y))/w,'tail_quadrant_frequency':sum(abs(a)>=statistics.median(map(abs,x)) and abs(b)>=statistics.median(map(abs,y)) for a,b in zip(x,y))/w})
 return {'schema':'qrds.factory.xawinwdo_discovery.v1','family':FAMILY,'generated_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'partition_read':'discovery_only','validation_read':False,'holdout_read':False,'windows_preregistered':WINDOWS,'results':results,'status':'DISCOVERY_COMPLETED_CANDIDATE_FREEZE_REQUIRED' if results else 'FAIL_CLOSED_INSUFFICIENT_DISCOVERY_ROWS','safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True}}
def main():
 a=argparse.ArgumentParser(); a.add_argument('--materialized',required=True); a.add_argument('--output',required=True); x=a.parse_args(); d=run(Path(x.materialized)); Path(x.output).write_text(json.dumps(d,indent=2)+'\n'); print(json.dumps({'status':d['status'],'windows':len(d['results'])}))
if __name__=='__main__':main()
