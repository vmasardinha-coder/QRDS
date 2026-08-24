#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math,sys
from pathlib import Path
import numpy as np,pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parent))
import gate_btc_b3_h30_h39_cross_asset as b
FAMS=tuple(f'H{i}' for i in range(50,60))
def add(R,f,s,g,a,side,i,h,p,bar): b.add(R,f,s,g,a,side,i,h,p,bar)
def ac1(x):
 x=np.asarray(x,float)
 return float(np.corrcoef(x[:-1],x[1:])[0,1]) if len(x)>3 and np.std(x[:-1])>0 and np.std(x[1:])>0 else np.nan
def gen(ss,bar):
 R=[];hist=[];prev=None
 for s,g in ss.items():
  n30=max(2,30//bar);n60=max(4,60//bar)
  if len(g)<=n60+2: continue
  q30=g.iloc[:n30];q60=g.iloc[:n60];feat={}
  for a in ('WIN','WDO'):
   o=float(g.iloc[0][f'open_{a}']); c30=float(q30.iloc[-1][f'close_{a}']); c60=float(q60.iloc[-1][f'close_{a}'])
   closes=q60[f'close_{a}'].astype(float).values; opens=q60[f'open_{a}'].astype(float).values
   rr=np.diff(np.log(closes)); path=float(np.sum(np.abs(np.diff(closes)))); er=abs(c60-o)/path if path>0 else 0
   pos=float(np.sum(rr[rr>0]**2)); neg=float(np.sum(rr[rr<0]**2)); semi=max(pos,neg)/max(min(pos,neg),1e-18); semis=1 if pos>=neg else -1
   hi=float(q60[f'high_{a}'].max()); lo=float(q60[f'low_{a}'].min()); up=hi-o; dn=o-lo
   ext=max(up,dn); exts=1 if up>=dn else -1; closemove=c60-o; rec=(ext-abs(c60-(hi if exts==1 else lo)))/ext if ext>0 else 0
   r30=float(q30[f'high_{a}'].max()-q30[f'low_{a}'].min()); b30hi=float(q30[f'high_{a}'].max()); b30lo=float(q30[f'low_{a}'].min()); after=q60.iloc[n30:]
   br=0
   if len(after):
    if float(after[f'high_{a}'].max())>b30hi: br=1
    elif float(after[f'low_{a}'].min())<b30lo: br=-1
   signed=np.sign(closes-opens)*q60[f'volume_{a}'].astype(float).values; sv=float(np.sum(signed))
   upper=(q30[f'high_{a}'].astype(float)-q30[[f'open_{a}',f'close_{a}']].astype(float).max(axis=1)).clip(lower=0)
   lower=(q30[[f'open_{a}',f'close_{a}']].astype(float).min(axis=1)-q30[f'low_{a}'].astype(float)).clip(lower=0)
   rng=(q30[f'high_{a}'].astype(float)-q30[f'low_{a}'].astype(float)).sum(); wick=float((upper.sum()-lower.sum())/rng) if rng>0 else 0
   feat[a]=dict(r30=(c30/o-1)*10000,r60=(c60/o-1)*10000,er=er,semi=semi,semis=semis,ext=ext,exts=exts,rec=rec,r30range=r30,br=br,sv=sv,ac=ac1(rr),wick=wick,session=(float(g.iloc[-1][f'close_{a}'])/o-1)*10000)
  if len(hist)>=20:
   for a in ('WIN','WDO'):
    H=hist[-20:]; meder=np.median([x[a]['er'] for x in H]); medabs60=np.median([abs(x[a]['r60']) for x in H]); medrange=np.median([x[a]['r30range'] for x in H]); medsv=np.median([abs(x[a]['sv']) for x in H]); medsess=np.median([abs(x[a]['session']) for x in H]);
    # H50
    for th,mode in [(1.25,'hi'),(1.5,'hi'),(.75,'lo'),(.60,'lo')]:
     cond=feat[a]['er']>=th*meder if mode=='hi' else feat[a]['er']<=th*meder
     if cond:
      sg=1 if feat[a]['r60']>0 else -1
      for hh in (60,120): add(R,'H50',s,g,a,sg,n60-1,hh,f'{mode}_{th}_same',bar);add(R,'H50',s,g,a,-sg,n60-1,hh,f'{mode}_{th}_inv',bar)
    # H51
    for th in (1.5,2.):
     if feat[a]['semi']>=th:
      sg=feat[a]['semis']
      for hh in (60,120): add(R,'H51',s,g,a,sg,n60-1,hh,f'dom_{th}',bar);add(R,'H51',s,g,a,-sg,n60-1,hh,f'inv_{th}',bar)
    # H53
    if medabs60>0:
     for th in (1.25,1.5):
      for rc in (.5,.75):
       if feat[a]['ext']>0 and abs(feat[a]['r60'])>=0 and feat[a]['ext']>=th*medabs60/10000*float(g.iloc[0][f'open_{a}']) and feat[a]['rec']>=rc:
        sg=-feat[a]['exts']
        for hh in (60,120): add(R,'H53',s,g,a,sg,n60-1,hh,f'{th}_{rc}_recovery',bar);add(R,'H53',s,g,a,-sg,n60-1,hh,f'{th}_{rc}_inv',bar)
    # H54
    if medrange>0:
     for th in (.6,.8):
      if feat[a]['r30range']<=th*medrange and feat[a]['br']:
       sg=feat[a]['br']
       for hh in (60,120): add(R,'H54',s,g,a,sg,n60-1,hh,f'break_{th}',bar);add(R,'H54',s,g,a,-sg,n60-1,hh,f'fade_{th}',bar)
    # H56
    if medabs60>0 and medsv>0 and np.sign(feat[a]['r60'])!=np.sign(feat[a]['sv']):
     for th in (1.,1.5):
      if abs(feat[a]['r60'])/medabs60>=th and abs(feat[a]['sv'])/medsv>=th:
       ps=1 if feat[a]['r60']>0 else -1; vs=1 if feat[a]['sv']>0 else -1
       for hh in (60,120): add(R,'H56',s,g,a,ps,n60-1,hh,f'price_{th}',bar);add(R,'H56',s,g,a,vs,n60-1,hh,f'volume_{th}',bar)
    # H57
    for th in (.25,.4):
     if math.isfinite(feat[a]['ac']) and abs(feat[a]['ac'])>=th:
      sg=1 if feat[a]['r60']>0 else -1; base=sg if feat[a]['ac']>0 else -sg
      for hh in (60,120): add(R,'H57',s,g,a,base,n60-1,hh,f'ac_{th}_base',bar);add(R,'H57',s,g,a,-base,n60-1,hh,f'ac_{th}_inv',bar)
    # H58
    for th in (.2,.35):
     if abs(feat[a]['wick'])>=th:
      sg=-1 if feat[a]['wick']>0 else 1
      for hh in (60,120): add(R,'H58',s,g,a,sg,n30-1,hh,f'pressure_{th}',bar);add(R,'H58',s,g,a,-sg,n30-1,hh,f'inv_{th}',bar)
    # H59
    if prev and medsess>0 and abs(hist[-1][a]['session'])>=medsess:
     psg=1 if hist[-1][a]['session']>0 else -1; csg=1 if feat[a]['r30']>0 else -1
     ratio=abs(hist[-1][a]['session'])/medsess
     for th in (1.,1.5):
      if ratio>=th:
       rel='same' if psg==csg else 'opp'
       for hh in (60,120): add(R,'H59',s,g,a,psg,n30-1,hh,f'{rel}_prior_{th}',bar);add(R,'H59',s,g,a,csg,n30-1,hh,f'{rel}_current_{th}',bar)
   # H52
   d=abs(feat['WIN']['er']-feat['WDO']['er'])
   for th in (.2,.35):
    if d>=th:
     lead='WIN' if feat['WIN']['er']>feat['WDO']['er'] else 'WDO'; lag='WDO' if lead=='WIN' else 'WIN'; sg=1 if feat[lead]['r60']>0 else -1
     for hh in (60,120): add(R,'H52',s,g,lag,sg,n60-1,hh,f'div_{th}',bar);add(R,'H52',s,g,lag,-sg,n60-1,hh,f'inv_{th}',bar)
   # H55
   scales={a:np.median([abs(x[a]['r60']) for x in hist[-20:]]) for a in ('WIN','WDO')}
   for leader,quiet in [('WIN','WDO'),('WDO','WIN')]:
    if scales[leader]>0 and scales[quiet]>0:
     for th in (1.25,1.5):
      if abs(feat[leader]['r60'])>=th*scales[leader] and abs(feat[quiet]['r60'])<=.6*scales[quiet]:
       sg=1 if feat[leader]['r60']>0 else -1
       for hh in (60,120): add(R,'H55',s,g,quiet,sg,n60-1,hh,f'async_{th}',bar);add(R,'H55',s,g,quiet,-sg,n60-1,hh,f'inv_{th}',bar)
  hist.append(feat);prev=s
 return pd.DataFrame(R)
def summ(t):
 out={};cells=[]
 for f in FAMS:
  q=[];ff=t[t.family==f] if len(t) else pd.DataFrame()
  if len(ff):
   for (asset,p,h),g in ff.groupby(['asset','param','horizon']):
    ok,re,m=b.metric(g,*b.COST[asset]);cells.append(dict(family=f,asset=asset,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));q+=([(asset,p,int(h))] if ok else [])
  legs=[]
  for a in ('WIN','WDO'):
   qa=[x for x in q if x[0]==a]; ps={x[1] for x in qa}; hs={x[2] for x in qa}
   if len(qa)>=2 and (len(ps)>=2 or len(hs)>=2): legs.append(a)
  out[f]={'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)}
 return out,cells
def main(out,ledger,cells):
 ds,dcov=b.sample(['2024_26'],5);rs,rcov=b.sample(['2020_22','2022_24'],15);D,dc=summ(gen(ds,5));R,rc=summ(gen(rs,15));cand=[f for f in FAMS if D[f]['survives']];surv=[f for f in cand if R[f]['survives']][:2];state={f:('SURVIVOR_REPLICATED' if f in surv else 'REJECTED_FAILED_REPLICATION' if f in cand else 'REJECTED_DISCOVERY') for f in FAMS};adequate=len(ds)>=300 and len(rs)>=600 and np.median(dcov)>=.95 and np.median(rcov)>=.95;status='DATA_INADEQUATE' if not adequate else 'SURVIVORS_READY_FOR_PROSPECTIVE' if surv else 'CLOSED_NO_H50_H59_SURVIVOR';p={'status':status,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'states':state,'discovery':D,'replication':R,'survivors':surv,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False};Path(out).write_text(json.dumps(p,indent=2,sort_keys=True));Path(ledger).write_text('\n'.join(json.dumps({'family':f,'generation':'H50_H59_V1','state':state[f],'discovery':D[f],'replication':R[f],'h1_economics_read':False,'survivor_partial_economics_read':False},sort_keys=True) for f in FAMS)+'\n');pd.DataFrame(dc+[{**x,'sample':'REPLICATION'} for x in rc]).to_csv(cells,index=False);print(json.dumps(p,indent=2,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--ledger',required=True);p.add_argument('--cells',required=True);a=p.parse_args();main(a.out,a.ledger,a.cells)
