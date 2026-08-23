#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gate_btc_b3_h30_h39_cross_asset as b
FAMS=tuple(f'H{i}' for i in range(40,50))
def add(R,f,s,g,a,side,i,h,p,bar): b.add(R,f,s,g,a,side,i,h,p,bar)
def gen(ss,bar):
 R=[];hist=[];prev=None
 for s,g in ss.items():
  n30=max(2,30//bar);n60=max(4,60//bar)
  if len(g)<=n60+2: continue
  q30=g.iloc[:n30];q60=g.iloc[:n60];ret={};rv={};sv={};first={};loc30={};loc60={}
  for a in ('WIN','WDO'):
   o=float(g.iloc[0][f'open_{a}']);c30=float(q30.iloc[-1][f'close_{a}']);c60=float(q60.iloc[-1][f'close_{a}']);ret[(a,30)]=(c30/o-1)*10000;ret[(a,60)]=(c60/o-1)*10000
   rr=np.diff(np.log(q60[f'close_{a}'].astype(float).values));rv[a]=float(np.sqrt(np.sum(rr*rr))*10000)
   signed=np.sign(q60[f'close_{a}'].astype(float).values-q60[f'open_{a}'].astype(float).values)*q60[f'volume_{a}'].astype(float).values;sv[a]=float(np.sum(signed))
   fr=float(g.iloc[0][f'high_{a}']-g.iloc[0][f'low_{a}']);fb=abs(float(g.iloc[0][f'close_{a}']-g.iloc[0][f'open_{a}']));first[a]=(fr,fb/fr if fr>0 else 0)
   for q,n,key in [(q30,n30,'30'),(q60,n60,'60')]:
    hi=float(q[f'high_{a}'].max());lo=float(q[f'low_{a}'].min());cl=float(q.iloc[-1][f'close_{a}']);v=(cl-lo)/(hi-lo) if hi>lo else .5
    (loc30 if key=='30' else loc60)[a]=v
  scales={a:{h:np.median([abs(x[f'r{h}_{a}']) for x in hist[-20:]]) if len(hist)>=20 else np.nan for h in (30,60)} for a in ('WIN','WDO')}
  for minute in (120,240):
   i=minute//bar-1
   if i+1<len(g) and len(hist)>=20:
    for leader,traded in [('WIN','WDO'),('WDO','WIN')]:
     cur=(float(g.iloc[i][f'close_{leader}'])/float(g.iloc[0][f'open_{leader}'])-1)*10000
     vals=[abs(x.get(f'r{minute}_{leader}',np.nan)) for x in hist[-20:] if math.isfinite(x.get(f'r{minute}_{leader}',np.nan))];sc=np.median(vals) if vals else np.nan
     if math.isfinite(sc) and sc>0:
      for th in (1.,1.5):
       if abs(cur)>=th*sc:
        sd=1 if cur>0 else -1
        for H in (60,120): add(R,'H40',s,g,traded,sd,i,H,f'{minute}_same_{th}',bar);add(R,'H40',s,g,traded,-sd,i,H,f'{minute}_opp_{th}',bar)
  if prev:
   pg=ss[prev]
   for a in ('WIN','WDO'):
    pr=float(pg[f'high_{a}'].max()-pg[f'low_{a}'].min());gap=float(g.iloc[0][f'open_{a}']-pg.iloc[-1][f'close_{a}'])
    if pr>0:
     for th in (.25,.5):
      if abs(gap)/pr>=th:
       gs=1 if gap>0 else -1;os=1 if ret[(a,30)]>0 else -1
       for sd,nm in [(gs,'cont'),(-gs,'fade')]: add(R,'H41',s,g,a,sd,n30-1,120,f'{"same" if os==gs else "opp"}_{nm}_{th}',bar)
   psgn={a:int(np.sign(float(pg.iloc[-1][f'close_{a}']/pg.iloc[0][f'open_{a}']-1))) for a in ('WIN','WDO')}
   for a in ('WIN','WDO'):
    pr=float(pg[f'high_{a}'].max()-pg[f'low_{a}'].min());gap=float(g.iloc[0][f'open_{a}']-pg.iloc[-1][f'close_{a}'])
    if pr>0:
     for th in (.25,.5):
      if abs(gap)/pr>=th:
       gs=1 if gap>0 else -1;rel='sameprev' if psgn['WIN']==psgn['WDO'] else 'oppprev'
       add(R,'H47',s,g,a,gs,n30-1,120,f'{rel}_cont_{th}',bar);add(R,'H47',s,g,a,-gs,n30-1,120,f'{rel}_fade_{th}',bar)
  for a in ('WIN','WDO'):
   if (loc30[a]<=.2 and loc60[a]>=.4) or (loc30[a]>=.8 and loc60[a]<=.6):
    sd=1 if loc60[a]>loc30[a] else -1
    add(R,'H42',s,g,a,sd,n60-1,60,'transition',bar);add(R,'H42',s,g,a,-sd,n60-1,60,'inverse',bar)
  if len(hist)>=20:
   for a in ('WIN','WDO'):
    medrv=np.median([x[f'rv_{a}'] for x in hist[-20:]]);medsv=np.median([abs(x[f'sv_{a}']) for x in hist[-20:]]);medfr=np.median([x[f'fr_{a}'] for x in hist[-20:]])
    if medrv>0:
     for th in (1.5,2.):
      if rv[a]>=th*medrv:
       sd=1 if ret[(a,60)]>0 else -1
       for H in (60,120): add(R,'H43',s,g,a,sd,n60-1,H,f'cont_{th}',bar);add(R,'H43',s,g,a,-sd,n60-1,H,f'fade_{th}',bar)
    if medsv>0:
     for th in (1.5,2.):
      if abs(sv[a])>=th*medsv:
       sd=1 if sv[a]>0 else -1
       for H in (60,120): add(R,'H44',s,g,a,sd,n60-1,H,f'cont_{th}',bar);add(R,'H44',s,g,a,-sd,n60-1,H,f'fade_{th}',bar)
    if medfr>0 and first[a][0]>=1.5*medfr:
     for th in (.5,.75):
      if first[a][1]>=th:
       sd=1 if float(g.iloc[0][f'close_{a}'])>float(g.iloc[0][f'open_{a}']) else -1
       for H in (60,120): add(R,'H46',s,g,a,sd,0,H,f'body_{th}',bar);add(R,'H46',s,g,a,-sd,0,H,f'inv_{th}',bar)
   for a in ('WIN','WDO'):
    sc30=scales[a][30];sc60=scales[a][60]
    if math.isfinite(sc30) and math.isfinite(sc60) and sc30>0 and sc60>0 and np.sign(ret[(a,30)])!=np.sign(ret[(a,60)]):
     for th in (.5,1.):
      if abs(ret[(a,30)])/sc30>=th and abs(ret[(a,60)])/sc60>=th:
       for H in (60,120): add(R,'H45',s,g,a,1 if ret[(a,60)]>0 else -1,n60-1,H,f'late_{th}',bar);add(R,'H45',s,g,a,1 if ret[(a,30)]>0 else -1,n60-1,H,f'early_{th}',bar)
   X=np.array([x['r30_WDO'] for x in hist[-20:]],float);Y=np.array([x['r30_WIN'] for x in hist[-20:]],float)
   if np.std(X)>0:
    beta=float(np.cov(X,Y,ddof=1)[0,1]/np.var(X,ddof=1));res=Y-beta*X;sd=float(np.std(res,ddof=1));cur=ret[('WIN',30)]-beta*ret[('WDO',30)]
    if sd>0:
     z=cur/sd
     for th in (1.5,2.):
      if abs(z)>=th:
       sg=1 if z>0 else -1
       for H in (60,120): add(R,'H48',s,g,'WIN',-sg,n30-1,H,f'conv_{th}',bar);add(R,'H48',s,g,'WIN',sg,n30-1,H,f'cont_{th}',bar)
   for a,other in [('WIN','WDO'),('WDO','WIN')]:
    medrv=np.median([x[f'rv_{a}'] for x in hist[-20:]]);hv=-1 if medrv>0 and rv[a]>=1.5*medrv else 0;v=sum([int(np.sign(ret[(a,30)])),int(np.sign(ret[(a,60)])),int(np.sign(ret[(other,30)])),hv])
    for th in (2,3):
     if abs(v)>=th:
      for H in (60,120): add(R,'H49',s,g,a,1 if v>0 else -1,n60-1,H,f'vote_{th}',bar)
  rec={}
  for a in ('WIN','WDO'):
   rec.update({f'r30_{a}':ret[(a,30)],f'r60_{a}':ret[(a,60)],f'rv_{a}':rv[a],f'sv_{a}':sv[a],f'fr_{a}':first[a][0]})
   for minute in (120,240):
    i=minute//bar-1;rec[f'r{minute}_{a}']=(float(g.iloc[i][f'close_{a}'])/float(g.iloc[0][f'open_{a}'])-1)*10000 if i<len(g) else np.nan
  hist.append(rec);prev=s
 return pd.DataFrame(R)
def summ(t):
 out={};cells=[]
 for f in FAMS:
  q=[];ff=t[t.family==f]
  for (asset,p,h),g in ff.groupby(['asset','param','horizon']):
   ok,re,m=b.metric(g,*b.COST[asset]);cells.append(dict(family=f,asset=asset,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));q+=([(asset,p,int(h))] if ok else [])
  legs=[]
  for a in ('WIN','WDO'):
   qa=[x for x in q if x[0]==a];ps={x[1] for x in qa};hs={x[2] for x in qa}
   if len(qa)>=2 and (len(ps)>=2 or len(hs)>=2): legs.append(a)
  out[f]={'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)}
 return out,cells
def main(out,ledger,cells):
 ds,dcov=b.sample(['2024_26'],5);rs,rcov=b.sample(['2020_22','2022_24'],15);D,dc=summ(gen(ds,5));R,rc=summ(gen(rs,15));cand=[f for f in FAMS if D[f]['survives']];surv=[f for f in cand if R[f]['survives']][:2];state={f:('SURVIVOR_REPLICATED' if f in surv else 'REJECTED_FAILED_REPLICATION' if f in cand else 'REJECTED_DISCOVERY') for f in FAMS};adequate=len(ds)>=300 and len(rs)>=600 and np.median(dcov)>=.95 and np.median(rcov)>=.95;status='DATA_INADEQUATE' if not adequate else 'SURVIVORS_READY_FOR_PROSPECTIVE' if surv else 'CLOSED_NO_H40_H49_SURVIVOR';p={'status':status,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'states':state,'discovery':D,'replication':R,'survivors':surv,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False};Path(out).write_text(json.dumps(p,indent=2,sort_keys=True));Path(ledger).write_text('\n'.join(json.dumps({'family':f,'generation':'H40_H49_V1','state':state[f],'discovery':D[f],'replication':R[f],'h1_economics_read':False,'survivor_partial_economics_read':False},sort_keys=True) for f in FAMS)+'\n');pd.DataFrame(dc+[{**x,'sample':'REPLICATION'} for x in rc]).to_csv(cells,index=False);print(json.dumps(p,indent=2,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--ledger',required=True);p.add_argument('--cells',required=True);a=p.parse_args();main(a.out,a.ledger,a.cells)
