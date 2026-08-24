#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from io import StringIO
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF = pd.Timestamp('2026-08-10')
THRESHOLDS=(1.0,1.5); HORIZONS=(60,120); ASSETS=('WIN','WDO'); MAPPINGS=('same','opposite')


def fetch_stooq():
    url='https://stooq.com/q/d/l/?s=%5Espx&i=d&d1=20190101&d2=20260809'
    r=requests.get(url,timeout=(10,60),headers={'User-Agent':'QRDS-research/1.0'}); r.raise_for_status(); raw=r.content
    z=pd.read_csv(StringIO(raw.decode('utf-8-sig')))
    need={'Date','Close'}
    if not need.issubset(z.columns): raise ValueError(f'Stooq schema missing {sorted(need-set(z.columns))}')
    x=z[['Date','Close']].rename(columns={'Date':'date','Close':'value'})
    x['date']=pd.to_datetime(x.date,errors='coerce'); x['value']=pd.to_numeric(x.value,errors='coerce')
    x=x.dropna().sort_values('date').drop_duplicates('date'); x=x[(x.date>=pd.Timestamp('2019-01-01'))&(x.date<CUTOFF)]
    if x.empty or x.date.duplicated().any() or not x.date.is_monotonic_increasing: raise ValueError('invalid Stooq series')
    return {'provider':'Stooq','symbol':'^SPX','instrument':'S&P 500 cash price index','url':r.url,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(x),'first':x.date.min().date().isoformat(),'last':x.date.max().date().isoformat()},x


def fetch_yahoo():
    p1=int(pd.Timestamp('2019-01-01',tz='UTC').timestamp()); p2=int(pd.Timestamp('2026-08-10',tz='UTC').timestamp())
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{quote("^GSPC",safe="")}?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true'
    r=requests.get(url,timeout=(10,60),headers={'User-Agent':'Mozilla/5.0 QRDS-research'}); r.raise_for_status(); raw=r.content; p=r.json()
    result=p['chart']['result'][0]; ts=result['timestamp']; closes=result['indicators']['quote'][0]['close']
    x=pd.DataFrame({'date':pd.to_datetime(ts,unit='s',utc=True).tz_convert(None).normalize(),'value':closes})
    x['value']=pd.to_numeric(x.value,errors='coerce'); x=x.dropna().sort_values('date').drop_duplicates('date'); x=x[(x.date>=pd.Timestamp('2019-01-01'))&(x.date<CUTOFF)]
    if x.empty: raise ValueError('empty Yahoo reference')
    return {'provider':'Yahoo Finance public chart reference','symbol':'^GSPC','url':r.url,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(x),'first':x.date.min().date().isoformat(),'last':x.date.max().date().isoformat()},x


def sanity(primary,ref):
    j=primary.merge(ref,on='date',suffixes=('_p','_r'))
    if len(j)<250: raise ValueError(f'insufficient overlap {len(j)}')
    j['rp']=j.value_p.pct_change(); j['rr']=j.value_r.pct_change(); q=j.dropna(subset=['rp','rr']).copy(); q=q[(q.rp!=0)&(q.rr!=0)]
    sign=float((np.sign(q.rp)==np.sign(q.rr)).mean()) if len(q) else 0.0
    med=float(np.median(np.abs(j.value_p/j.value_r-1)))
    if sign<0.99 or med>0.0025: raise ValueError(f'sanity mismatch sign={sign:.6f} median_rel={med:.6f}')
    return {'overlap_rows':len(j),'return_sign_agreement':sign,'median_abs_relative_close_difference':med,'status':'PASS'}


def coverage(x,sessions):
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session'); d=x.sort_values('date')
    j=pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False); age=(j.session-j.date).dt.days; ok=j.value.notna()&age.notna()&(age<=5)
    return float(ok.mean()),int(ok.sum()),int(len(j)),int(age.dropna().max()) if age.notna().any() else None


def signals(x,sessions):
    d=x.copy().sort_values('date'); d['move']=d.value.pct_change(); d['scale']=d.move.abs().shift(1).rolling(20,min_periods=20).median(); d['z']=d.move/d.scale
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session'); j=pd.merge_asof(left,d[['date','move','z']],left_on='session',right_on='date',direction='backward',allow_exact_matches=False); j['age']=(j.session-j.date).dt.days; j=j[(j.age>=1)&(j.age<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.move) and pd.notna(r.z)}


def add(rows,s,g,asset,side,h,param,bar):
    ei=h//bar
    if ei>=len(g): return
    col=f'open_{asset}'; gross=b.rb(side,float(g.iloc[0][col]),float(g.iloc[ei][col])); dei=1+h//bar; delay=b.rb(side,float(g.iloc[1][col]),float(g.iloc[dei][col])) if dei<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family='H61',session=s,asset=asset,side=side,param=param,horizon=h,gross=gross,delay=delay))


def generate(ss,bar,sig):
    rows=[]
    for s,g in ss.items():
        r=sig.get(s)
        if r is None: continue
        mv=float(r.move); z=float(r.z)
        if not math.isfinite(mv) or not math.isfinite(z) or mv==0: continue
        sign=1 if mv>0 else -1
        for th in THRESHOLDS:
            if abs(z)<th: continue
            for asset in ASSETS:
                for mapping in MAPPINGS:
                    side=sign if mapping=='same' else -sign
                    for h in HORIZONS: add(rows,s,g,asset,side,h,f'{mapping}_{th}',bar)
    return pd.DataFrame(rows)


def summarize(t):
    q=[]; cells=[]
    if t.empty:return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (asset,param,h),g in t.groupby(['asset','param','horizon']):
        ok,reasons,m=b.metric(g,*b.COST[asset]); cells.append(dict(family='H61',asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(reasons),**m));
        if ok:q.append((asset,param,int(h)))
    legs=[]
    for asset in ASSETS:
        qa=[x for x in q if x[0]==asset]
        if len(qa)>=2 and (len({x[1] for x in qa})>=2 or len({x[2] for x in qa})>=2): legs.append(asset)
    return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells


def main(out,cells,ledger):
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    result={'state':'DATA_GAP','discovery':None,'replication':None}; source={}; allcells=[]
    try:
        pm,x=fetch_stooq(); rm,y=fetch_yahoo(); check=sanity(x,y); dcvf,dn,dt,dm=coverage(x,ds); rcvf,rn,rt,rmxd=coverage(x,rs)
        source={**pm,'sanity_reference':rm,'sanity':check,'discovery_join_coverage':dcvf,'replication_join_coverage':rcvf,'discovery_join_n':f'{dn}/{dt}','replication_join_n':f'{rn}/{rt}','max_stale_days_discovery':dm,'max_stale_days_replication':rmxd}
        if dcvf<.90 or rcvf<.90: raise ValueError('causal join coverage below 90%')
        source['status']='PASS'; source['economics_run']=True
        D,dc=summarize(generate(ds,5,signals(x,ds))); R,rc=summarize(generate(rs,15,signals(x,rs)))
        state='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'; result={'state':state,'source':source,'discovery':D,'replication':R}; allcells=[dict(sample='DISCOVERY',**z) for z in dc]+[dict(sample='REPLICATION',**z) for z in rc]
    except Exception as exc:
        source.update({'status':'DATA_GAP','gap_type':'PUBLIC_MIRROR_OR_SANITY_QA_FAILED','error':f'{type(exc).__name__}: {str(exc)[:500]}','economics_run':False,'synthetic_backfill':False}); result={'state':'DATA_GAP','source':source,'discovery':None,'replication':None}
    p={'schema':'gate_btc.b3.h61.public_mirror_recovery.v1','cutoff_exclusive':'2026-08-10','result':result,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'h1_economics_read':False,'survivor_partial_economics_read':False,'synthetic_backfill':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n'); pd.DataFrame(allcells).to_csv(cells,index=False); Path(ledger).write_text(json.dumps({'family':'H61','generation':'H60_H69_V1','state':result['state'],'source':result.get('source',{}),'discovery':result.get('discovery'),'replication':result.get('replication'),'orders':0,'capital':0,'engine_feed':False},sort_keys=True)+'\n'); print(json.dumps(p,indent=2,sort_keys=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',required=True); ap.add_argument('--cells',required=True); ap.add_argument('--ledger',required=True); a=ap.parse_args(); main(a.out,a.cells,a.ledger)
