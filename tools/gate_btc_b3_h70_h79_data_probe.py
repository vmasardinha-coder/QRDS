#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from io import StringIO
from pathlib import Path
import pandas as pd, requests

import gate_btc_b3_h60_h69_data_probe as h60
import gate_btc_b3_h64_eia_wti as h64

CUTOFF=pd.Timestamp('2026-08-10')


def clean(z,date_col,value_col):
    x=pd.DataFrame({'date':pd.to_datetime(z[date_col],errors='coerce'), 'value':pd.to_numeric(z[value_col],errors='coerce')})
    x=x.dropna().sort_values('date').drop_duplicates('date')
    x=x[(x.date>=pd.Timestamp('2019-01-01')) & (x.date<CUTOFF)]
    if x.empty or x.date.duplicated().any() or not x.date.is_monotonic_increasing: raise ValueError('invalid series')
    return x


def fetch_treasury_curve():
    frames=[]; raw=[]; urls=[]
    for year in range(2019,2027):
        url=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all'
        params={'type':'daily_treasury_yield_curve','field_tdr_date_value':str(year),'page':'','_format':'csv'}
        r=requests.get(url,params=params,timeout=(5,35),headers={'User-Agent':'QRDS-research/1.0'}); r.raise_for_status(); raw.append(r.content); urls.append(r.url)
        z=pd.read_csv(StringIO(r.content.decode('utf-8-sig'))); cols={str(c).strip():c for c in z.columns}
        if not {'Date','2 Yr','10 Yr'} <= set(cols): raise ValueError(f'unexpected Treasury schema {year}')
        frames.append(z[[cols['Date'],cols['2 Yr'],cols['10 Yr']]].rename(columns={cols['Date']:'date',cols['2 Yr']:'us2y',cols['10 Yr']:'us10y'}))
    z=pd.concat(frames,ignore_index=True); z['date']=pd.to_datetime(z.date,errors='coerce'); z['us2y']=pd.to_numeric(z.us2y,errors='coerce'); z['us10y']=pd.to_numeric(z.us10y,errors='coerce')
    z=z.dropna().sort_values('date').drop_duplicates('date'); z=z[(z.date>=pd.Timestamp('2019-01-01'))&(z.date<CUTOFF)]
    if z.empty: raise ValueError('Treasury curve empty')
    z['slope']=z.us10y-z.us2y
    meta={'provider':'U.S. Department of the Treasury','series':'2Y/10Y Par Yield Curve','url':urls[-1],'sha256':hashlib.sha256(b'\n'.join(raw)).hexdigest(),'rows':len(z),'first':z.date.min().date().isoformat(),'last':z.date.max().date().isoformat(),'delivery_path':'official_yearly_csv'}
    return meta,z


def fetch_cboe(symbol):
    url=f'https://cdn.cboe.com/api/global/us_indices/daily_prices/{symbol}_History.csv'
    r=requests.get(url,timeout=(5,35),headers={'User-Agent':'QRDS-research/1.0'}); r.raise_for_status(); raw=r.content
    z=pd.read_csv(StringIO(raw.decode('utf-8-sig'))); cols={str(c).strip().upper():c for c in z.columns}
    if 'DATE' not in cols or 'CLOSE' not in cols: raise ValueError(f'unexpected Cboe {symbol} schema')
    x=clean(z,cols['DATE'],cols['CLOSE'])
    return {'provider':'Cboe Global Markets','series':symbol,'url':r.url,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(x),'first':x.date.min().date().isoformat(),'last':x.date.max().date().isoformat(),'delivery_path':'official_csv'},x


def coverage(x,sessions,value='value'):
    d=x[['date',value]].rename(columns={value:'value'}).sort_values('date'); left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j=pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False); age=(j.session-j.date).dt.days
    ok=j.value.notna() & age.notna() & (age>=1) & (age<=5)
    return float(ok.mean()),f'{int(ok.sum())}/{len(j)}'


def qa(meta,x,disc,repl,value='value'):
    dc,dn=coverage(x,disc,value); rc,rn=coverage(x,repl,value); meta=dict(meta); meta.update({'discovery_join_coverage':dc,'replication_join_coverage':rc,'discovery_join_n':dn,'replication_join_n':rn,'status':'PASS' if dc>=.90 and rc>=.90 else 'DATA_GAP_COVERAGE'}); return meta


def main(out):
    disc=h60.session_dates(['2024_26'],5); repl=h60.session_dates(['2020_22','2022_24'],15); series={}
    try:
        m,x=fetch_treasury_curve(); series['TREASURY_CURVE']=qa(m,x,disc,repl,'slope')
    except Exception as e: series['TREASURY_CURVE']={'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
    for sym in ('VIX','VIX9D'):
        try: m,x=fetch_cboe(sym); series[sym]=qa(m,x,disc,repl)
        except Exception as e: series[sym]={'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
    try:
        m,x=h60.fetch_bcb_brlusd(); series['BRLUSD']=qa(m,x,disc,repl)
    except Exception as e: series['BRLUSD']={'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
    try:
        m,x=h64.fetch_eia(); series['WTI']=qa(m,x,disc,repl)
    except Exception as e: series['WTI']={'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
    req={
      'H70':['TREASURY_CURVE'],'H71':['TREASURY_CURVE'],'H72':['VIX'],'H73':['VIX','VIX9D'],'H74':['TREASURY_CURVE'],
      'H75':['BRLUSD','TREASURY_CURVE'],'H76':['WTI','TREASURY_CURVE'],'H77':['BRLUSD','VIX','WTI','TREASURY_CURVE'],
      'H78':['BRLUSD','VIX','WTI','TREASURY_CURVE'],'H79':['BRLUSD','VIX','WTI','TREASURY_CURVE']}
    fam={f:{'status':'DATA_READY' if all(series.get(s,{}).get('status')=='PASS' for s in rs) else 'DATA_GAP','missing_or_failed':[s for s in rs if series.get(s,{}).get('status')!='PASS']} for f,rs in req.items()}
    p={'schema':'gate_btc.b3.h70_h79.data_probe.v1','economics_run':False,'cutoff_exclusive':'2026-08-10','discovery_sessions':len(disc),'replication_sessions':len(repl),'series':series,'families':fam,'observed_sources':['TREASURY_CURVE','VIX','VIX9D','BRLUSD','WTI'],'derived_features':['10Y_minus_2Y_slope','VIX9D_over_VIX','shock_vote','cross_market_dispersion','rolling_causal_residual'],'h1_economics_read':False,'survivor_partial_economics_read':False,'synthetic_backfill':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n'); print(json.dumps(p,indent=2,sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); z=a.parse_args(); main(z.out)
