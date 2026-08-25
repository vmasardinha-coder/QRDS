#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
import gate_btc_b3_h30_h39_cross_asset as b
import gate_btc_b3_h110_h119_features as f
FAMS=tuple(f'H{i}' for i in range(110,120));ASSETS=('WIN','WDO');H=(60,120);GEN='H110_H119_V1'
def emit(R,fam,s,g,a,sd,p,bar,i=-1):
 for h in H:b.add(R,fam,s,g,a,int(sd),i,h,p,bar)
def stress(R,fam,s,g,sg,p,bar):
 for a,base in [('WIN',-sg),('WDO',sg)]:emit(R,fam,s,g,a,base,'stress_'+p,bar);emit(R,fam,s,g,a,-base,'inverse_'+p,bar)
def residuals(ss,m):
 out={};hist=[];keys=sorted(ss);ret={s:(float(g.iloc[-1].close_WIN)/float(g.iloc[0].open_WIN)-1)*1e4 for s,g in ss.items()}
 for i,s in enumerate(keys):
  if i==0:continue
  ps=keys[i-1];r=m.get(ps)
  if r is None:continue
  x=np.array([r.term,r.vvix,r.vxeem],float);y=ret[ps]
  if np.all(np.isfinite(x)):
   if len(hist)>=60:
    q=hist[-60:];X=np.array([z[0] for z in q]);Y=np.array([z[1] for z in q]);A=np.c_[np.ones(len(X)),X];bt=np.linalg.lstsq(A,Y,rcond=None)[0];rh=Y-A@bt;sd=np.std(rh)
    if sd>0:out[s]=(y-np.r_[1.,x]@bt)/sd
   hist.append((x,y))
 return out
def gen(ss,bar,feat):
 m=f.map_sessions(feat,ss);rz=residuals(ss,m);R=[]
 for s,g in ss.items():
  r=m.get(s)
  if r is None:continue
  term=float(r.term) if pd.notna(r.term) else np.nan
  for th in (1.,1.1):
   if math.isfinite(term) and term>=th:stress(R,'H110',s,g,1,f'term_ge_{th:.2f}',bar)
  for th in (.9,.85):
   if math.isfinite(term) and term<=th:stress(R,'H110',s,g,-1,f'term_le_{th:.2f}',bar)
  for fam,k in [('H111','vvix_zchg'),('H112','ovx_zchg'),('H113','gvz_zchg'),('H114','vxeem_zchg')]:
   v=getattr(r,k)
   if pd.notna(v):
    for th in (1.,1.5):
     if abs(v)>=th:stress(R,fam,s,g,1 if v>0 else -1,f'z{th}',bar)
  vs=[]
  for sy in ('VIX9D','VVIX','OVX','GVZ','VXEEM'):
   v=getattr(r,'d_'+sy)
   if pd.notna(v) and v!=0:vs.append(1 if v>0 else -1)
  if len(vs)==5:
   po=sum(v>0 for v in vs);ne=5-po;al=max(po,ne);sg=1 if po>ne else -1
   for q in (3,4):
    if al>=q:stress(R,'H115',s,g,sg,f'{q}of5',bar)
  vv=r.vvix_zchg
  if pd.notna(vv):
   for tt in (1.,1.1):
    for z in (1.,1.5):
     if term>=tt and vv>=z:stress(R,'H116',s,g,1,f'term{tt:.2f}_vvixz{z}',bar)
  dz=r.dispersion_zchg
  if pd.notna(dz):
   for th in (1.,1.5):
    if abs(dz)>=th:stress(R,'H117',s,g,1 if dz>0 else -1,f'disp_z{th}',bar)
  sm,sg,psg=r.stress_mag,r.stress_sign,r.prev_stress_sign
  if all(pd.notna(x) for x in (sm,sg,psg)):
   for th in (.75,1.):
    if sg!=0 and sg==psg and abs(sm)>=th:stress(R,'H118',s,g,int(sg),f'persist_z{th}',bar)
  z=rz.get(s)
  if z is not None:
   n=max(2,30//bar)
   if len(g)>n:
    x=(float(g.iloc[n-1].close_WIN)/float(g.iloc[0].open_WIN)-1)*1e4;sg=1 if x>0 else -1 if x<0 else 0
    for th in (1.5,2.):
     if sg and abs(z)>=th:emit(R,'H119',s,g,'WIN',sg,f'continuation_residz{th}',bar,n-1);emit(R,'H119',s,g,'WIN',-sg,f'meanrev_residz{th}',bar,n-1)
 return pd.DataFrame(R)
def summ(t,fam):
 q=[];cells=[]
 if t.empty:return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
 for (a,p,h),g in t[t.family==fam].groupby(['asset','param','horizon']):
  ok,re,m=b.metric(g,*b.COST[a]);cells.append(dict(family=fam,asset=a,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));q+=([(a,p,int(h))] if ok else [])
 legs=[]
 for a in ASSETS:
  z=[x for x in q if x[0]==a]
  if len(z)>=2 and (len({x[1] for x in z})>=2 or len({x[2] for x in z})>=2):legs.append(a)
 return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells
def main(o,l,c):
 feat,src=f.build();ds,dc=b.sample(['2024_26'],5);rs,rc=b.sample(['2020_22','2022_24'],15);D=gen(ds,5,feat);R=gen(rs,15,feat);disc={};rep={};st={};cc=[]
 for fam in FAMS:
  a,x=summ(D,fam);z,y=summ(R,fam);disc[fam]=a;rep[fam]=z;cc += [{**v,'sample':'DISCOVERY'} for v in x]+[{**v,'sample':'REPLICATION'} for v in y];st[fam]='SURVIVOR_REPLICATED' if a['survives'] and z['survives'] else 'REJECTED_FAILED_REPLICATION' if a['survives'] else 'REJECTED_DISCOVERY'
 sv=[x for x in FAMS if st[x]=='SURVIVOR_REPLICATED'][:2];p={'schema':'gate_btc.b3.h110_h119.economics.v1','status':'SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE' if sv else 'CLOSED_NO_H110_H119_SURVIVOR','cutoff_exclusive':'2026-08-10','states':st,'discovery':disc,'replication':rep,'survivors':sv,'source_series':src,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dc)),'replication_median_common_bar_coverage':float(np.median(rc)),'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True};Path(o).parent.mkdir(parents=True,exist_ok=True);Path(o).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
 with Path(l).open('w') as h:
  for fam in FAMS:h.write(json.dumps({'family':fam,'generation':GEN,'state':st[fam],'discovery':disc[fam],'replication':rep[fam],'orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n')
 pd.DataFrame(cc).to_csv(c,index=False);print(json.dumps({'status':p['status'],'states':st,'survivors':sv},sort_keys=True))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--ledger',required=True);a.add_argument('--cells',required=True);z=a.parse_args();main(z.out,z.ledger,z.cells)
