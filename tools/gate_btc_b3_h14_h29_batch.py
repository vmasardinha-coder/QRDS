#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from io import StringIO
from pathlib import Path
import numpy as np,pandas as pd,requests
FAMS=tuple(f'H{i}' for i in range(14,30)); CUTOFF=pd.Timestamp('2026-08-10',tz='America/Sao_Paulo')
MIN_N=60; MIN_SIDE=15; MIN_BUCKET=15; MAX_TOP5=.40
COST={'WIN':(2.,3.),'WDO':(1.5,2.5)}
def num(s):return pd.to_numeric(s.astype(str).str.replace('.','',regex=False).str.replace(',','.',regex=False),errors='coerce')
def half(s):d=pd.Timestamp(s);return f'{d.year}H{1 if d.month<=6 else 2}'
def rb(side,e,x):return side*(x/e-1)*10000 if e>0 and x>0 else np.nan
def load(asset,period,tf):
 url=f'https://raw.githubusercontent.com/wesleyzilva/tradetech/main/CandlesHistoryDatas/{period}/{asset}FUT_F_0_{tf}min.csv';r=requests.get(url,timeout=180);r.raise_for_status();x=pd.read_csv(StringIO(r.text),sep=';',dtype=str);c={z.lower().strip():z for z in x.columns};d=pd.DataFrame();d['timestamp']=pd.to_datetime(x[c['data']].str.strip()+' '+x[c['hora']].str.strip(),dayfirst=True)
 for a,b in [('abertura','open'),('máximo','high'),('mínimo','low'),('fechamento','close'),('quantidade','volume')]:d[b]=num(x[c[a]])
 d=d.dropna().sort_values('timestamp').drop_duplicates('timestamp');d['timestamp']=d.timestamp.dt.tz_localize('America/Sao_Paulo');d=d[d.timestamp<CUTOFF];d['session']=d.timestamp.dt.date.astype(str);return d
def sessions(d,bar):
 out={}
 for s,g in d.groupby('session'):
  g=g.sort_values('timestamp').reset_index(drop=True);dt=g.timestamp.diff().dropna().dt.total_seconds()
  if len(g)>=max(30,180//bar) and (g.iloc[0].timestamp.hour,g.iloc[0].timestamp.minute)==(9,0) and not (dt!=bar*60).any():out[s]=g
 return out
def add(R,f,s,g,side,i,h,p,bar):
 e=i+1;x=e+h//bar;de=e+1;dx=de+h//bar
 if side and x<len(g):
  a=rb(side,float(g.iloc[e].open),float(g.iloc[x].open));b=rb(side,float(g.iloc[de].open),float(g.iloc[dx].open)) if dx<len(g) else np.nan
  if math.isfinite(a):R.append(dict(family=f,session=s,side=side,param=p,horizon=h,gross=a,delay=b))
def gen(ss,bar):
 R=[];keys=sorted(ss);hist=[];prev=None
 for s in keys:
  g=ss[s];o=float(g.iloc[0].open); n15=max(1,15//bar);n30=max(2,30//bar);n60=max(3,60//bar); q30=g.iloc[:n30]; q60=g.iloc[:n60]; hi30=float(q30.high.max());lo30=float(q30.low.min());mv30=float(q30.iloc[-1].close)-o;r30=hi30-lo30
  medr=np.median([x[0] for x in hist[-20:]]) if len(hist)>=20 else np.nan; medv=np.median([x[1] for x in hist[-20:]]) if len(hist)>=20 else np.nan
  # H14 opening range break/rejection: first close outside 30m range
  for i in range(n30,min(len(g)-1,120//bar)):
   c=float(g.iloc[i].close)
   if c>hi30 or c<lo30:
    sd=1 if c>hi30 else -1;add(R,'H14',s,g,sd,i,60,'orb_cont',bar);add(R,'H14',s,g,-sd,i,60,'orb_reject',bar);break
  if prev:
   pg=ss[prev];pc=float(pg.iloc[-1].close);pr=float(pg.high.max()-pg.low.min());gap=o-pc
   if pr>0 and abs(gap)<=3*pr:
    for th in (.25,.5):
     if abs(gap)>=th*pr:
      sd=1 if gap>0 else -1;add(R,'H15',s,g,sd,0,60,f'gap_cont_{th}',bar);add(R,'H15',s,g,-sd,0,60,f'gap_fade_{th}',bar)
    z=abs(gap)/pr
    for th in (.5,1.):
     if z>=th:add(R,'H16',s,g,-1 if gap>0 else 1,0,120,f'normgap_{th}',bar)
  # H17 efficiency; H18 wick/body
  path=np.abs(np.diff(q30.close.astype(float))).sum();eff=abs(mv30)/path if path else 0
  for th in (.5,.7):
   if eff>=th and mv30:add(R,'H17',s,g,1 if mv30>0 else -1,n30-1,120,f'eff_{th}',bar)
  body=abs(float(q30.iloc[-1].close)-o);upper=hi30-max(o,float(q30.iloc[-1].close));lower=min(o,float(q30.iloc[-1].close))-lo30
  if body>0:
   for th in (1.,2.):
    if upper/body>=th:add(R,'H18',s,g,-1,n30-1,60,f'wick_{th}',bar)
    if lower/body>=th:add(R,'H18',s,g,1,n30-1,60,f'wick_{th}',bar)
  if math.isfinite(medv) and medv>0:
   vr=float(q30.volume.sum())/medv
   for th in (1.5,2.):
    if vr>=th and mv30:add(R,'H19',s,g,1 if mv30>0 else -1,n30-1,120,f'volacc_{th}',bar)
  # VWAP state/displacement
  if q60.volume.sum()>0:
   v=float((((q60.high+q60.low+q60.close)/3)*q60.volume).sum()/q60.volume.sum());last=float(q60.iloc[-1].close);rng=float(q60.high.max()-q60.low.min())
   cross=np.sign(q60.close.astype(float)-v);changes=int((cross.values[1:]*cross.values[:-1]<0).sum())
   if changes>=1:add(R,'H20',s,g,1 if last>v else -1,n60-1,60,f'vwap_recross_{min(changes,2)}',bar)
   if rng>0:
    z=abs(last-v)/rng
    for th in (.25,.5):
     if z>=th:add(R,'H21',s,g,-1 if last>v else 1,n60-1,60,f'vwapz_{th}',bar)
  # rolling breakout / failed breakout
  look=max(3,30//bar)
  for i in range(look,min(len(g)-2,180//bar)):
   h=float(g.iloc[i-look:i].high.max());l=float(g.iloc[i-look:i].low.min());c=float(g.iloc[i].close)
   if c>h or c<l:
    sd=1 if c>h else -1;add(R,'H22',s,g,sd,i,60,'roll_break',bar)
    nxt=float(g.iloc[i+1].close)
    if (sd==1 and nxt<h) or (sd==-1 and nxt>l):add(R,'H23',s,g,-sd,i+1,60,'failed_break',bar)
    break
  # autocorr, standardized impulse, vol compression expansion
  rr=np.diff(np.log(q60.close.astype(float).values))
  if len(rr)>=6:
   ac=np.corrcoef(rr[:-1],rr[1:])[0,1]
   if math.isfinite(ac) and abs(ac)>=.2 and mv30:add(R,'H24',s,g,(1 if mv30>0 else -1)*(1 if ac>0 else -1),n60-1,60,'ac_02',bar)
   sd=np.std(rr,ddof=1);imp=rr[-1]/sd if sd>0 else 0
   for th in (1.5,2.):
    if abs(imp)>=th:add(R,'H25',s,g,-1 if imp>0 else 1,n60-1,60,f'imp_{th}',bar)
  if math.isfinite(medr) and medr>0 and r30<=.75*medr:
   for i in range(n30,min(len(g)-1,120//bar)):
    c=float(g.iloc[i].close)
    if c>hi30 or c<lo30:add(R,'H26',s,g,1 if c>hi30 else -1,i,120,'compress_expand',bar);break
  # price-volume divergence
  if len(q60)>=4:
   pm=float(q60.iloc[-1].close)-float(q60.iloc[0].open);vh=float(q60.iloc[len(q60)//2:].volume.mean());vl=float(q60.iloc[:len(q60)//2].volume.mean())
   if pm and vl>0 and vh/vl<=.8:add(R,'H27',s,g,-1 if pm>0 else 1,n60-1,60,'pv_div',bar)
  # seasonality conditioned on opening sign; simple ex-ante vote
  if mv30:
   for minute in (120,240):
    i=minute//bar-1
    if i+1<len(g):add(R,'H28',s,g,1 if mv30>0 else -1,i,60,f'open_sign_{minute}',bar)
   votes=[]
   votes.append(1 if mv30>0 else -1)
   if eff>=.5:votes.append(1 if mv30>0 else -1)
   if math.isfinite(medv) and medv>0 and float(q30.volume.sum())/medv>=1.5:votes.append(1 if mv30>0 else -1)
   if len(votes)>=2 and abs(sum(votes))>=2:add(R,'H29',s,g,1 if sum(votes)>0 else -1,n30-1,120,'simple_vote',bar)
  hist.append((r30,float(q30.volume.sum())));prev=s
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
def summ(t,asset):
 c1,c2=COST[asset];out={};cells=[]
 for f in FAMS:
  qs=[];ff=t[t.family==f]
  for (p,h),g in ff.groupby(['param','horizon']):
   ok,re,m=metric(g,c1,c2);cells.append(dict(asset=asset,family=f,param=p,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));qs+=([(p,int(h))] if ok else [])
  ps={x[0] for x in qs};hs={x[1] for x in qs};out[f]={'qualified_cells':len(qs),'survives':len(qs)>=2 and (len(ps)>=2 or len(hs)>=2),'qualified':sorted(f'{p}|{h}' for p,h in qs)}
 return out,cells
def main(out,ledger,cells):
 final={};allcells=[]
 for asset in ('WIN','WDO'):
  ds=sessions(load(asset,'2024_26',5),5);disc,dc=summ(gen(ds,5),asset)
  old=pd.concat([load(asset,'2020_22',15),load(asset,'2022_24',15)]).sort_values('timestamp').drop_duplicates('timestamp');rs=sessions(old,15);rep,rc=summ(gen(rs,15),asset)
  cand=[f for f in FAMS if disc[f]['survives']];surv=[f for f in cand if rep[f]['survives']][:2];state={f:('SURVIVOR_REPLICATED' if f in surv else 'REJECTED_FAILED_REPLICATION' if f in cand else 'REJECTED_DISCOVERY') for f in FAMS};final[asset]={'discovery_sessions':len(ds),'replication_sessions':len(rs),'states':state,'discovery':disc,'replication':rep,'survivors':surv};allcells+=dc+[{**x,'sample':'REPLICATION'} for x in rc]
 payload={'status':'SURVIVORS_READY_FOR_PROSPECTIVE' if any(final[a]['survivors'] for a in final) else 'CLOSED_NO_H14_H29_SURVIVOR','assets':final,'h1_economics_read':False,'h1_contaminated':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'source':'wesleyzilva/tradetech community Profit exports','continuous_series_use':'scale_invariant_research_only; roll-like overnight gaps excluded'};Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(payload,indent=2,sort_keys=True));
 with Path(ledger).open('w') as f:
  for a in final:
   for fam in FAMS:f.write(json.dumps({'asset':a,'family':fam,'generation':'H14_H29_V1','state':final[a]['states'][fam],'discovery':final[a]['discovery'][fam],'replication':final[a]['replication'][fam],'h1_economics_read':False,'orders':0,'capital':0},sort_keys=True)+'\n')
 pd.DataFrame(allcells).to_csv(cells,index=False);print(json.dumps(payload,indent=2,sort_keys=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--ledger',required=True);p.add_argument('--cells',required=True);a=p.parse_args();main(a.out,a.ledger,a.cells)
