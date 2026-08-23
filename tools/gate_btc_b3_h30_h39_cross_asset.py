#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from io import StringIO
from pathlib import Path
import numpy as np,pandas as pd,requests
FAMS=tuple(f'H{i}' for i in range(30,40));CUTOFF=pd.Timestamp('2026-08-10',tz='America/Sao_Paulo');MIN_N=60;MIN_SIDE=15;MIN_BUCKET=15;MAX_TOP5=.40;COST={'WIN':(2.,3.),'WDO':(1.5,2.5)}
SOURCE_REPO='wesleyzilva/tradetech';SOURCE_COMMIT='0deb43c668dcd447ed169c9cafb52af625d5419e'
def num(s):return pd.to_numeric(s.astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),errors='coerce')
def half(s):d=pd.Timestamp(s);return f'{d.year}H{1 if d.month<=6 else 2}'
def rb(side,e,x):return side*(x/e-1)*10000 if e>0 and x>0 else np.nan
def load(a,p,tf):
 u=f'https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/CandlesHistoryDatas/{p}/{a}FUT_F_0_{tf}min.csv';r=requests.get(u,timeout=180);r.raise_for_status();x=pd.read_csv(StringIO(r.text),sep=';',dtype=str);c={z.lower().strip():z for z in x.columns};d=pd.DataFrame();d['timestamp']=pd.to_datetime(x[c['data']].str.strip()+' '+x[c['hora']].str.strip(),dayfirst=True)
 for q,n in [('abertura','open'),('máximo','high'),('mínimo','low'),('fechamento','close'),('quantidade','volume')]:d[n]=num(x[c[q]])
 d=d.dropna().sort_values('timestamp').drop_duplicates('timestamp');d.timestamp=d.timestamp.dt.tz_localize('America/Sao_Paulo');d=d[d.timestamp<CUTOFF];d['session']=d.timestamp.dt.date.astype(str);return d
def sess(d,bar):
 o={}
 for s,g in d.groupby('session'):
  g=g.sort_values('timestamp').reset_index(drop=True);dt=g.timestamp.diff().dropna().dt.total_seconds()
  if len(g)>=max(30,180//bar) and (g.iloc[0].timestamp.hour,g.iloc[0].timestamp.minute)==(9,0) and not (dt!=bar*60).any():o[s]=g
 return o
def sync(a,b):
 out={};cov=[]
 for s in sorted(set(a)&set(b)):
  x=a[s].merge(b[s],on='timestamp',suffixes=('_WIN','_WDO'));den=max(len(a[s]),len(b[s]));cv=len(x)/den if den else 0
  if len(x)>=min(len(a[s]),len(b[s]))*.95:out[s]=x
  cov.append(cv)
 return out,cov
def add(R,f,s,g,asset,side,i,h,p,bar):
 e=i+1;x=e+h//bar;de=e+1;dx=de+h//bar;c=f'open_{asset}'
 if side and x<len(g):
  a=rb(side,float(g.iloc[e][c]),float(g.iloc[x][c]));b=rb(side,float(g.iloc[de][c]),float(g.iloc[dx][c])) if dx<len(g) else np.nan
  if math.isfinite(a):R.append(dict(family=f,session=s,asset=asset,side=side,param=p,horizon=h,gross=a,delay=b))
def gen(ss,bar):
 R=[];hist=[]
 for s,g in ss.items():
  n30=max(2,30//bar);n60=max(4,60//bar)
  if len(g)<=n60+1:continue
  q30=g.iloc[:n30];q60=g.iloc[:n60];ret={};z={};rv={};vdisp={}
  for a in ('WIN','WDO'):
   o=float(g.iloc[0][f'open_{a}']);c30=float(q30.iloc[-1][f'close_{a}']);c60=float(q60.iloc[-1][f'close_{a}']);ret[(a,30)]=(c30/o-1)*10000;ret[(a,60)]=(c60/o-1)*10000
   rr=np.diff(np.log(q60[f'close_{a}'].astype(float).values));rv[a]=float(np.sqrt(np.sum(rr*rr))*10000)
   vol=q60[f'volume_{a}'].astype(float);typ=(q60[f'high_{a}'].astype(float)+q60[f'low_{a}'].astype(float)+q60[f'close_{a}'].astype(float))/3;vw=float((typ*vol).sum()/vol.sum()) if vol.sum()>0 else c60;rng=float(q60[f'high_{a}'].max()-q60[f'low_{a}'].min());vdisp[a]=(c60-vw)/rng if rng>0 else 0
  scales={a:{h:np.median([abs(x[(a,h)]) for x in hist[-20:]]) if len(hist)>=20 else np.nan for h in (30,60)} for a in ('WIN','WDO')}
  for a in ('WIN','WDO'):
   for h in (30,60):z[(a,h)]=ret[(a,h)]/scales[a][h] if math.isfinite(scales[a][h]) and scales[a][h]>0 else np.nan
  for leader,traded,f in [('WIN','WDO','H30'),('WDO','WIN','H31')]:
   for hh,i in [(30,n30-1),(60,n60-1)]:
    if math.isfinite(z[(leader,hh)]):
     for th in (1.,1.5):
      if abs(z[(leader,hh)])>=th:
       sd=1 if ret[(leader,hh)]>0 else -1
       for H in (60,120):add(R,f,s,g,traded,sd,i,H,f'{hh}_same_{th}',bar);add(R,f,s,g,traded,-sd,i,H,f'{hh}_opp_{th}',bar)
  if all(math.isfinite(z[(a,30)]) for a in ('WIN','WDO')):
   dif=z[('WIN',30)]-z[('WDO',30)];lag='WDO' if dif>0 else 'WIN';leadsgn=1 if dif>0 else -1
   for th in (1.,1.5):
    if abs(dif)>=th:
     for H in (60,120):add(R,'H32',s,g,lag,leadsgn,n30-1,H,f'div_{th}',bar);add(R,'H33',s,g,lag,-leadsgn,n30-1,H,f'div_{th}',bar)
  if len(hist)>=20:
   ratios=[x['rv_WIN']/x['rv_WDO'] for x in hist[-20:] if x['rv_WDO']>0];med=np.median(ratios) if ratios else np.nan;ratio=rv['WIN']/rv['WDO'] if rv['WDO']>0 else np.nan
   if math.isfinite(med) and med>0 and math.isfinite(ratio):
    for th in (1.5,2.):
     high='WIN' if ratio/med>=th else 'WDO' if med/ratio>=th else None
     if high:
      sd=1 if ret[(high,60)]>0 else -1
      for H in (60,120):add(R,'H34',s,g,high,sd,n60-1,H,f'volratio_{th}',bar)
  sw=np.sign(ret[('WIN',30)]);sd=np.sign(ret[('WDO',30)])
  if sw and sd:
   for th in (.5,1.):
    if all(math.isfinite(z[(a,30)]) and abs(z[(a,30)])>=th for a in ('WIN','WDO')):
     for a,sg in [('WIN',int(sw)),('WDO',int(sd))]:
      for H in (60,120):add(R,'H35' if sw==sd else 'H36',s,g,a,sg if sw==sd else -sg,n30-1,H,f'mag_{th}',bar)
   for a,sg in [('WIN',int(sw)),('WDO',int(sd))]:
    for inv in (1,-1):add(R,'H37',s,g,a,int(sg*inv),n30-1,120,f'{int(sw)}_{int(sd)}_{a}_{"own" if inv==1 else "inverse"}',bar)
  dif=vdisp['WIN']-vdisp['WDO'];lag='WDO' if dif>0 else 'WIN';sg=1 if dif>0 else -1
  for th in (.25,.5):
   if abs(dif)>=th:add(R,'H38',s,g,lag,sg,n60-1,60,f'conv_{th}',bar);add(R,'H38',s,g,lag,-sg,n60-1,60,f'cont_{th}',bar)
  for a,other in [('WIN','WDO'),('WDO','WIN')]:
   votes=[int(np.sign(ret[(a,30)])),int(np.sign(ret[(other,30)])),int(np.sign(vdisp[a]))];v=sum(votes)
   if abs(v)>=2:
    for H in (60,120):add(R,'H39',s,g,a,1 if v>0 else -1,n60-1,H,'vote2',bar)
  hist.append({('WIN',30):ret[('WIN',30)],('WIN',60):ret[('WIN',60)],('WDO',30):ret[('WDO',30)],('WDO',60):ret[('WDO',60)],'rv_WIN':rv['WIN'],'rv_WDO':rv['WDO']})
 return pd.DataFrame(R)
def metric(g,c1,c2):
 a=g.gross.astype(float);d=g.delay.dropna().astype(float);z=g.copy();z['half']=z.session.map(half);sides={int(k):(len(x),float((x.gross-c1).mean())) for k,x in g.groupby('side')};b={k:(len(x),float((x.gross-c1).mean())) for k,x in z.groupby('half')};pos=a[a>0].sort_values(ascending=False);top=float(pos.head(5).sum()/pos.sum()) if pos.sum()>0 else 1.;re=[]
 if len(g)<MIN_N:re+=['MIN_TRADES']
 if float((a-c1).mean())<=.25:re+=['EDGE']
 if float((a-c2).mean())<=0:re+=['STRESS']
 if len(d)<MIN_N or float((d-c1).mean())<=0:re+=['DELAY']
 if set(sides)!={-1,1} or any(n<MIN_SIDE or x<=0 for n,x in sides.values()):re+=['SIDES']
 eb=[x for x in b.values() if x[0]>=MIN_BUCKET]
 if len(eb)<2 or any(x[1]<=0 for x in eb):re+=['CALENDAR']
 if top>MAX_TOP5:re+=['CONCENTRATION']
 return not re,re,{'n':len(g),'net':float((a-c1).mean()),'stress':float((a-c2).mean()),'delay':float((d-c1).mean()) if len(d) else None,'top5':top}
def summ(t):
 out={};cells=[]
 for f in FAMS:
  q=[];ff=t[t.family==f]
  for (asset,p,h),g in ff.groupby(['asset','param','horizon']):
   ok,re,m=metric(g,*COST[asset]);cells.append(dict(family=f,asset=asset,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));q+=([(asset,p,int(h))] if ok else [])
  survive=[]
  for a in ('WIN','WDO'):
   qa=[x for x in q if x[0]==a];ps={x[1] for x in qa};hs={x[2] for x in qa}
   if len(qa)>=2 and (len(ps)>=2 or len(hs)>=2):survive.append(a)
  out[f]={'qualified_cells':len(q),'surviving_legs':survive,'survives':bool(survive),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)}
 return out,cells
def sample(periods,bar):
 A={}
 for a in ('WIN','WDO'):
  d=pd.concat([load(a,p,bar) for p in periods]).sort_values('timestamp').drop_duplicates('timestamp');A[a]=sess(d,bar)
 ss,cov=sync(A['WIN'],A['WDO']);return ss,cov
def main(out,ledger,cells):
 ds,dcov=sample(['2024_26'],5);rs,rcov=sample(['2020_22','2022_24'],15);D,dc=summ(gen(ds,5));R,rc=summ(gen(rs,15));cand=[f for f in FAMS if D[f]['survives']];surv=[f for f in cand if R[f]['survives']][:2];state={f:('SURVIVOR_REPLICATED' if f in surv else 'REJECTED_FAILED_REPLICATION' if f in cand else 'REJECTED_DISCOVERY') for f in FAMS};adequate=len(ds)>=300 and len(rs)>=600 and np.median(dcov)>=.95 and np.median(rcov)>=.95;status='DATA_INADEQUATE' if not adequate else 'SURVIVORS_READY_FOR_PROSPECTIVE' if surv else 'CLOSED_NO_H30_H39_SURVIVOR';p={'status':status,'source_repo':SOURCE_REPO,'source_commit':SOURCE_COMMIT,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dcov)) if dcov else 0,'replication_median_common_bar_coverage':float(np.median(rcov)) if rcov else 0,'states':state,'discovery':D,'replication':R,'survivors':surv,'h1_economics_read':False,'h1_contaminated':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False};Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(p,indent=2,sort_keys=True));
 with Path(ledger).open('w') as f:
  for fam in FAMS:f.write(json.dumps({'family':fam,'generation':'H30_H39_V1','state':state[fam],'discovery':D[fam],'replication':R[fam],'h1_economics_read':False,'orders':0,'capital':0},sort_keys=True)+'\n')
 pd.DataFrame(dc+[{**x,'sample':'REPLICATION'} for x in rc]).to_csv(cells,index=False);print(json.dumps(p,indent=2,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--ledger',required=True);p.add_argument('--cells',required=True);a=p.parse_args();main(a.out,a.ledger,a.cells)
