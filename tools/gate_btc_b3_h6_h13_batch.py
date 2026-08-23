#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import numpy as np,pandas as pd,requests

H1_CUTOFF=pd.Timestamp('2026-08-10',tz='America/Sao_Paulo')
REF_COST=2.0; STRESS_COST=3.0; MIN_TRADES=60; MIN_SIDE=15; MIN_BUCKET=15; MIN_EDGE=.25; MAX_TOP5=.40
FAMILIES=('H6','H7','H8','H9','H10','H11','H12','H13'); MAX_SURVIVORS=2

def half(s):
 d=pd.Timestamp(s); return f'{d.year}H{1 if d.month<=6 else 2}'
def rb(side,e,x): return side*(x/e-1)*10000 if e>0 and x>0 else np.nan

def load_discovery(csv,meta):
 m=json.loads(Path(meta).read_text())
 assert m.get('h1_economics_read') is False and m.get('absolute_level_research_allowed') is False
 d=pd.read_csv(csv); t=pd.to_datetime(d.timestamp)
 t=t.dt.tz_localize('America/Sao_Paulo') if t.dt.tz is None else t.dt.tz_convert('America/Sao_Paulo')
 d['timestamp']=t
 if (t>=H1_CUTOFF).any(): raise RuntimeError('H1_CUTOFF_BREACH')
 d['session']=t.dt.date.astype(str)
 return d

def sessions(d,bar=5):
 out={}
 for s,g in d.groupby('session',sort=True):
  g=g.sort_values('timestamp').reset_index(drop=True)
  if len(g)<max(30,150//bar) or (g.loc[0,'timestamp'].hour,g.loc[0,'timestamp'].minute)!=(9,0): continue
  dt=g.timestamp.diff().dropna().dt.total_seconds()
  if len(dt) and (dt!=bar*60).any(): continue
  out[s]=g
 return out

def trailing_stats(ss,bar):
 keys=sorted(ss); hist=[]; out={}
 n30=30//bar
 for s in keys:
  out[s]={}
  if len(hist)>=20:
   h=hist[-20:]; out[s]={'range30':float(np.median([x[0] for x in h])),'vol30':float(np.median([x[1] for x in h]))}
  g=ss[s]; o=float(g.iloc[0].open); q=g.iloc[:n30]
  hist.append(((float(q.high.max())-float(q.low.min()))/o,float(q.volume.sum())))
 return out

def add(rows,fam,s,g,side,signal_idx,horizon,param,bar):
 entry=signal_idx+1; hb=horizon//bar; ex=entry+hb; de=entry+1; dx=de+hb
 if side==0 or ex>=len(g): return
 gross=rb(side,float(g.iloc[entry].open),float(g.iloc[ex].open)); delayed=np.nan
 if dx<len(g): delayed=rb(side,float(g.iloc[de].open),float(g.iloc[dx].open))
 if math.isfinite(gross): rows.append(dict(family=fam,session=s,side=side,param=param,horizon=horizon,gross_bps=gross,delayed_gross_bps=delayed))

def generate(ss,bar):
 rows=[]; keys=sorted(ss); tr=trailing_stats(ss,bar); prev=None
 for s in keys:
  g=ss[s]; o=float(g.iloc[0].open); n30=30//bar; n60=60//bar
  # H6: large overnight gap fade, normalized by previous full-session range; roll-like gaps excluded.
  if prev is not None:
   pg=ss[prev]; pc=float(pg.iloc[-1].close); pr=float(pg.high.max()-pg.low.min())
   gap=o-pc
   if pr>0 and abs(gap)<=3*pr:
    for th in (.25,.5,.75):
     if abs(gap)>=th*pr: add(rows,'H6',s,g,-1 if gap>0 else 1,0,60,f'gapfade_{th}',bar)
  # H7: VWAP displacement fade at fixed 30/60 minute observations, scaled by observed range.
  for mins in (30,60):
   n=mins//bar; q=g.iloc[:n]; rng=float(q.high.max()-q.low.min())
   if rng>0 and q.volume.sum()>0:
    v=float(((q.high+q.low+q.close)/3*q.volume).sum()/q.volume.sum()); disp=float(q.iloc[-1].close)-v
    for th in (.5,1.0):
     if abs(disp)>=th*rng: add(rows,'H7',s,g,-1 if disp>0 else 1,n-1,60,f'vwap_{mins}_{th}',bar)
  # H8: compressed first 30m then first close outside that range; continuation.
  st=tr.get(s,{})
  if st.get('range30'):
   q=g.iloc[:n30]; r=(float(q.high.max())-float(q.low.min()))/o
   for ct in (.5,.75):
    if r<=ct*st['range30']:
     hi=float(q.high.max()); lo=float(q.low.min())
     for i in range(n30,min(len(g)-1,120//bar)):
      c=float(g.iloc[i].close)
      if c>hi or c<lo:
       side=1 if c>hi else -1
       for h in (60,120): add(rows,'H8',s,g,side,i,h,f'compress_{ct}',bar)
       break
  # H9: opening volume surprise + price confirmation, continuation.
  if st.get('vol30'):
   q=g.iloc[:n30]; vr=float(q.volume.sum())/st['vol30']; move=float(q.iloc[-1].close)-o
   for vt in (1.5,2.0):
    if vr>=vt and move!=0:
     for h in (60,120): add(rows,'H9',s,g,1 if move>0 else -1,n30-1,h,f'vol_{vt}',bar)
  # H10: first confirmed break of previous session high/low; continuation. Exclude roll-like gaps.
  if prev is not None:
   pg=ss[prev]; ph=float(pg.high.max()); pl=float(pg.low.min()); pr=ph-pl; pc=float(pg.iloc[-1].close)
   if pr>0 and abs(o-pc)<=3*pr:
    for i in range(max(1,15//bar),min(len(g)-1,120//bar)):
     c=float(g.iloc[i].close)
     if c>ph or c<pl:
      side=1 if c>ph else -1
      for h in (60,120): add(rows,'H10',s,g,side,i,h,'prev_extreme_break',bar)
      break
  # H11: close location in cumulative range; continuation from extremes.
  for mins in (30,60):
   n=mins//bar; q=g.iloc[:n]; hi=float(q.high.max()); lo=float(q.low.min())
   if hi>lo:
    loc=(float(q.iloc[-1].close)-lo)/(hi-lo)
    for th in (.75,.85):
     if loc>=th or loc<=1-th: add(rows,'H11',s,g,1 if loc>=th else -1,n-1,60,f'loc_{mins}_{th}',bar)
  # H12: fixed time-of-day momentum; times are preregistered, not searched continuously.
  for minute in (60,120,240,300):
   i=minute//bar-1; lb=30//bar
   if i>=lb and i+1<len(g):
    mv=float(g.iloc[i].close)-float(g.iloc[i-lb+1].open)
    if mv!=0: add(rows,'H12',s,g,1 if mv>0 else -1,i,60,f'tod_{minute}',bar)
  # H13: realized-volatility state at 60m: high-vol trend / low-vol reversal of last 15m move.
  if n60<=len(g):
   q=g.iloc[:n60]; rets=np.diff(np.log(q.close.astype(float).values)); short=max(1,15//bar)
   if len(rets)>=max(3,short):
    longv=float(np.std(rets,ddof=1)); shortv=float(np.std(rets[-short:],ddof=1)) if short>1 else abs(float(rets[-1]))
    ratio=shortv/longv if longv>0 else 0; mv=float(q.iloc[-1].close)-float(q.iloc[-short].open)
    if mv!=0:
     if ratio>=1.5: add(rows,'H13',s,g,1 if mv>0 else -1,n60-1,60,'highvol_trend_1.5',bar)
     if ratio<=.67: add(rows,'H13',s,g,-1 if mv>0 else 1,n60-1,60,'lowvol_revert_0.67',bar)
  prev=s
 return pd.DataFrame(rows)

def metrics(g):
 gross=g.gross_bps.astype(float); delayed=g.delayed_gross_bps.dropna().astype(float)
 sides={('LONG' if int(k)==1 else 'SHORT'):{'n':len(x),'net':float((x.gross_bps-REF_COST).mean())} for k,x in g.groupby('side')}
 z=g.copy(); z['half']=z.session.map(half); buckets={k:{'n':len(x),'net':float((x.gross_bps-REF_COST).mean())} for k,x in z.groupby('half')}
 pos=gross[gross>0].sort_values(ascending=False); top=float(pos.head(5).sum()/pos.sum()) if pos.sum()>0 else 1
 return {'trades':len(g),'net2':float((gross-REF_COST).mean()),'net3':float((gross-STRESS_COST).mean()),'delayed_n':len(delayed),'delayed_net2':float((delayed-REF_COST).mean()) if len(delayed) else None,'sides':sides,'buckets':buckets,'top5':top}
def qualify(m):
 r=[]
 if m['trades']<MIN_TRADES:r+=['MIN_TRADES']
 if m['net2']<=MIN_EDGE:r+=['REFERENCE_COST_EDGE']
 if m['net3']<=0:r+=['STRESS_COST']
 if m['delayed_n']<MIN_TRADES or m['delayed_net2'] is None or m['delayed_net2']<=0:r+=['DELAYED_ENTRY']
 if set(m['sides'])!={'LONG','SHORT'} or any(x['n']<MIN_SIDE or x['net']<=0 for x in m['sides'].values()):r+=['SIDE_STABILITY']
 eb=[x for x in m['buckets'].values() if x['n']>=MIN_BUCKET]
 if len(eb)<2 or any(x['net']<=0 for x in eb):r+=['CALENDAR_STABILITY']
 if m['top5']>MAX_TOP5:r+=['CONCENTRATION']
 return len(r)==0,r

def summarize(t):
 out={}; cells=[]
 for fam in FAMILIES:
  f=t[t.family==fam] if len(t) else pd.DataFrame()
  qs=[]
  if len(f):
   for (p,h),g in f.groupby(['param','horizon']):
    m=metrics(g); ok,why=qualify(m); cells.append({'family':fam,'param':p,'horizon':int(h),'qualified':ok,'reasons':why,**m})
    if ok:qs.append((p,int(h)))
  params={x[0] for x in qs}; horizons={x[1] for x in qs}
  # Family must show >=2 neighboring/config cells, not a single lucky parameter.
  survive=len(qs)>=2 and (len(params)>=2 or len(horizons)>=2)
  out[fam]={'qualified_cells':len(qs),'survives_discovery':survive,'qualified_params':sorted([f'{p}|{h}' for p,h in qs])}
 return out,cells

def br_num(s): return pd.to_numeric(s.astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),errors='raise')
def old_history():
 frames=[]; prov=[]; sess=requests.Session(); sess.headers.update({'User-Agent':'QRDS-H6-H13/1.0'})
 for dr in ('CandlesHistoryDatas/2020_22','CandlesHistoryDatas/2022_24'):
  api=f'https://api.github.com/repos/wesleyzilva/tradetech/contents/{dr}/WINFUT_F_0_15min.csv?ref=main'; m=sess.get(api,timeout=60);m.raise_for_status();j=m.json();r=sess.get(j['download_url'],timeout=180);r.raise_for_status()
  x=pd.read_csv(StringIO(r.text),sep=';',dtype=str); c={z.lower().strip():z for z in x.columns}; d=pd.DataFrame();d['timestamp']=pd.to_datetime(x[c['data']].str.strip()+' '+x[c['hora']].str.strip(),dayfirst=True);d['symbol']=x[c['ativo']].str.strip().str.upper()
  for a,b in [('abertura','open'),('máximo','high'),('mínimo','low'),('fechamento','close'),('quantidade','volume')]:d[b]=br_num(x[c[a]])
  d=d[(d.symbol=='WINFUT')&(d.timestamp<pd.Timestamp('2024-06-19'))];frames.append(d);prov.append({'dir':dr,'sha':j.get('sha'),'rows':len(d)})
 d=pd.concat(frames).sort_values('timestamp').drop_duplicates('timestamp',keep='last');d['timestamp']=d.timestamp.dt.tz_localize('America/Sao_Paulo');d['session']=d.timestamp.dt.date.astype(str);return d,prov

def main(csv,meta,out,ledger,cells):
 d=load_discovery(csv,meta); ss=sessions(d,5); t=generate(ss,5); disc,dc=summarize(t); candidates=[f for f in FAMILIES if disc[f]['survives_discovery']]
 od,prov=old_history(); oss=sessions(od,15); ot=generate(oss,15); rep,rc=summarize(ot)
 survivors=[f for f in candidates if rep[f]['survives_discovery']][:MAX_SURVIVORS]
 state={f:('SURVIVOR_REPLICATED' if f in survivors else 'REJECTED_FAILED_REPLICATION' if f in candidates else 'REJECTED_DISCOVERY') for f in FAMILIES}
 payload={'status':'SURVIVORS_READY_FOR_PROSPECTIVE' if survivors else 'CLOSED_NO_H6_H13_SURVIVOR','families':state,'discovery_sessions':len(ss),'replication_sessions':len(oss),'discovery':disc,'replication':rep,'activated_candidates':survivors,'h1_economics_read':False,'h1_contaminated':False,'orders_generated':0,'real_capital_used':0,'promotion_allowed':False,'engine_feed':False,'replication_source':prov}
 Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(payload,indent=2,sort_keys=True))
 with Path(ledger).open('w') as f:
  for fam in FAMILIES:f.write(json.dumps({'family':fam,'generation':'H6_H13_V1','state':state[fam],'discovery':disc[fam],'replication':rep[fam],'h1_economics_read':False,'orders':0,'capital':0},sort_keys=True)+'\n')
 pd.DataFrame(dc+[{**x,'sample':'REPLICATION'} for x in rc]).to_csv(cells,index=False)
 print(json.dumps(payload,indent=2,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--csv',required=True);p.add_argument('--metadata',required=True);p.add_argument('--out',required=True);p.add_argument('--ledger',required=True);p.add_argument('--cells',required=True);a=p.parse_args();main(a.csv,a.metadata,a.out,a.ledger,a.cells)
