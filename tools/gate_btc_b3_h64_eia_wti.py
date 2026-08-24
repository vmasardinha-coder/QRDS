#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, io, json, math
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF = pd.Timestamp('2026-08-10')
URL = 'https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls'
THRESHOLDS=(1.0,1.5)
HORIZONS=(60,120)
MAPPINGS=('same','opposite')
ASSETS=('WIN','WDO')
PARSER_VERSION='eia-rwtcd-v1'


def fetch_eia():
    r=requests.get(URL,timeout=(10,60),headers={'User-Agent':'QRDS-research/1.0'})
    r.raise_for_status(); raw=r.content
    if len(raw)<1000: raise ValueError('implausibly small EIA workbook')
    sheets=pd.read_excel(io.BytesIO(raw),sheet_name=None,header=None,engine='xlrd')
    candidates=[]
    for sheet_name,df in sheets.items():
        for header_row in range(min(12,len(df))):
            row=[str(x).strip().lower() for x in df.iloc[header_row].tolist()]
            date_cols=[i for i,x in enumerate(row) if x=='date' or 'date'==x.strip()]
            value_cols=[i for i,x in enumerate(row) if 'wti' in x and ('spot' in x or 'cushing' in x)]
            if not date_cols or not value_cols: continue
            di,vi=date_cols[0],value_cols[0]
            z=df.iloc[header_row+1:,[di,vi]].copy(); z.columns=['date','value']
            z['date']=pd.to_datetime(z['date'],errors='coerce')
            z['value']=pd.to_numeric(z['value'],errors='coerce')
            z=z.dropna().sort_values('date').drop_duplicates('date')
            z=z[(z.date>=pd.Timestamp('2019-01-01')) & (z.date<CUTOFF)]
            if not z.empty: candidates.append((len(z),sheet_name,header_row,z))
    if not candidates: raise ValueError('EIA WTI date/value schema not found')
    _,sheet,header,z=max(candidates,key=lambda x:x[0])
    if z.date.duplicated().any() or not z.date.is_monotonic_increasing: raise ValueError('invalid EIA date order')
    meta={'name':'WTI','series':'Cushing OK WTI Spot Price FOB','provider':'U.S. Energy Information Administration','delivery_path':'official_xls_history','url':r.url,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'sheet':str(sheet),'header_row_zero_based':int(header),'parser_version':PARSER_VERSION,'rows':len(z),'first':z.date.min().date().isoformat(),'last':z.date.max().date().isoformat()}
    return meta,z


def coverage(x,sessions):
    d=x[['date','value']].sort_values('date')
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j=pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    age=(j.session-j.date).dt.days
    ok=j.value.notna() & age.notna() & (age>=1) & (age<=5)
    return float(ok.mean()),int(ok.sum()),int(len(j)),int(age.dropna().max()) if age.notna().any() else None


def signals(x,sessions):
    d=x[['date','value']].copy().sort_values('date')
    d['move']=d['value'].pct_change(); d['scale']=d['move'].abs().shift(1).rolling(20,min_periods=20).median(); d['z']=d['move']/d['scale']
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j=pd.merge_asof(left,d[['date','move','z']],left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    j['age_days']=(j.session-j.date).dt.days; j=j[(j.age_days>=1)&(j.age_days<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def add(rows,s,g,asset,side,h,param,bar):
    entry=0; exit_i=h//bar; dentry=1; dexit=dentry+h//bar
    if exit_i>=len(g): return
    col=f'open_{asset}'; gross=b.rb(side,float(g.iloc[entry][col]),float(g.iloc[exit_i][col])); delay=b.rb(side,float(g.iloc[dentry][col]),float(g.iloc[dexit][col])) if dexit<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family='H64',session=s,asset=asset,side=side,param=param,horizon=h,gross=gross,delay=delay))


def generate(ss,bar,sig):
    rows=[]
    for s,g in ss.items():
        x=sig.get(s)
        if x is None: continue
        z=float(x.z); mv=float(x.move)
        if not math.isfinite(z) or not math.isfinite(mv) or mv==0: continue
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
        ok,reasons,m=b.metric(g,*b.COST[asset]); cells.append(dict(family='H64',asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(reasons),**m))
        if ok:q.append((asset,param,int(h)))
    legs=[]
    for asset in ASSETS:
        qa=[x for x in q if x[0]==asset]
        if len(qa)>=2 and (len({x[1] for x in qa})>=2 or len({x[2] for x in qa})>=2):legs.append(asset)
    return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells


def main(out,ledger,cells):
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    try:
        meta,x=fetch_eia(); dc,dn,dt,dm=coverage(x,ds); rc,rn,rt,rm=coverage(x,rs)
        meta.update({'discovery_join_coverage':dc,'replication_join_coverage':rc,'discovery_join_n':f'{dn}/{dt}','replication_join_n':f'{rn}/{rt}','max_stale_days_discovery':dm,'max_stale_days_replication':rm})
        if dc<.90 or rc<.90: raise ValueError(f'coverage below gate discovery={dc} replication={rc}')
        meta['status']='PASS'; meta['economics_run']=True
        D,dcells=summarize(generate(ds,5,signals(x,ds))); R,rcells=summarize(generate(rs,15,signals(x,rs)))
        state='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
    except Exception as exc:
        meta={'name':'WTI','provider':'U.S. Energy Information Administration','url':URL,'status':'DATA_GAP','gap_type':'PROVENANCE_SCHEMA_OR_DELIVERY','error_type':type(exc).__name__,'error':str(exc)[:500],'economics_run':False}; D=R=None; dcells=rcells=[]; state='DATA_GAP'
    p={'schema':'gate_btc.b3.h64.eia_wti.v1','family':'H64','state':state,'cutoff_exclusive':'2026-08-10','source':meta,'discovery':D,'replication':R,'thresholds':list(THRESHOLDS),'mappings':list(MAPPINGS),'horizons':list(HORIZONS),'h1_economics_read':False,'survivor_partial_economics_read':False,'synthetic_backfill':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n'); Path(ledger).write_text(json.dumps({'family':'H64','generation':'H60_H69_V1','state':state,'source':meta,'discovery':D,'replication':R,'orders':0,'capital':0,'engine_feed':False},sort_keys=True)+'\n'); pd.DataFrame([dict(sample='DISCOVERY',**x) for x in dcells]+[dict(sample='REPLICATION',**x) for x in rcells]).to_csv(cells,index=False)
    print(json.dumps({'state':state,'source_status':meta.get('status'),'source':meta.get('provider')},sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--ledger',required=True);a.add_argument('--cells',required=True);z=a.parse_args();main(z.out,z.ledger,z.cells)
