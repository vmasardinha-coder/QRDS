#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from io import StringIO
from pathlib import Path
import pandas as pd, requests
import gate_btc_b3_h30_h39_cross_asset as b

OUT=Path('artifacts/b3_h110_h119/B3_H110_H119_CBOE_SOURCE_QA.json')
BASE='https://cdn.cboe.com/api/global/us_indices/daily_prices/'
SYMS=('VIX','VIX9D','VVIX','OVX','GVZ','VXEEM')
DEPENDENCIES={
 'H110':('VIX9D','VIX'), 'H111':('VVIX','VIX'), 'H112':('OVX','VIX'), 'H113':('GVZ','VIX'),
 'H114':('VXEEM','VIX'), 'H115':('VIX9D','VVIX','OVX','GVZ','VXEEM'), 'H116':('VIX9D','VIX','VVIX'),
 'H117':('VIX','OVX','GVZ','VXEEM'), 'H118':('VIX9D','VVIX','OVX','GVZ','VXEEM'),
 'H119':('VIX9D','VIX','VVIX','VXEEM')
}
CUTOFF=pd.Timestamp('2026-08-10')

def fetch(sym):
    url=BASE+f'{sym}_History.csv'
    r=requests.get(url,timeout=(5,45),headers={'User-Agent':'QRDS-research-source-QA/1.0'}); r.raise_for_status(); raw=r.content
    x=pd.read_csv(StringIO(raw.decode('utf-8-sig'))); cols={c.strip().upper():c for c in x.columns}
    if 'DATE' not in cols or 'CLOSE' not in cols: raise ValueError(f'{sym} unexpected schema {list(x.columns)}')
    d=pd.DataFrame({'date':pd.to_datetime(x[cols['DATE']],errors='coerce',dayfirst=False),'close':pd.to_numeric(x[cols['CLOSE']],errors='coerce')}).dropna().sort_values('date').drop_duplicates('date')
    d=d[(d.date>=pd.Timestamp('2019-01-01'))&(d.date<CUTOFF)]
    if d.empty or d.date.duplicated().any() or not d.date.is_monotonic_increasing: raise ValueError(f'{sym} invalid history')
    return d,{'provider':'Cboe Global Markets','url':r.url,'raw_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(d),'first':d.date.min().date().isoformat(),'last':d.date.max().date().isoformat(),'schema':list(x.columns),'date_semantics':'US month/day/year','duplicate_dates':False}

def coverage(d,sessions):
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j=pd.merge_asof(left,d[['date','close']].sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    age=(j.session-j.date).dt.days; ok=j.close.notna()&age.notna()&(age>=1)&(age<=5)
    return {'coverage':float(ok.mean()) if len(j) else 0.0,'joined':int(ok.sum()),'sessions':int(len(j)),'max_join_age_days':int(age[ok].max()) if ok.any() else None}

def main():
    OUT.parent.mkdir(parents=True,exist_ok=True)
    ds,_=b.sample(['2024_26'],5); rs,_=b.sample(['2020_22','2022_24'],15)
    series={}; meta={}; errors={}
    for sym in SYMS:
        try:
            d,m=fetch(sym); series[sym]=d; m['discovery']=coverage(d,ds); m['replication']=coverage(d,rs); meta[sym]=m
        except Exception as e: errors[sym]=type(e).__name__+': '+str(e)[:300]
    fam={}
    for f,deps in DEPENDENCIES.items():
        missing=[s for s in deps if s not in series]
        low=[s for s in deps if s in meta and (meta[s]['discovery']['coverage']<.90 or meta[s]['replication']['coverage']<.90)]
        status='SOURCE_READY' if not missing and not low else 'DATA_GAP_CBOE_SOURCE_OR_COVERAGE'
        fam[f]={'status':status,'dependencies':list(deps),'missing':missing,'below_coverage_gate':low}
    p={'schema':'gate_btc.b3.h110_h119.cboe_source_qa.v1','status':'SOURCE_QA_READY' if all(v['status']=='SOURCE_READY' for v in fam.values()) else 'SOURCE_QA_PARTIAL_DATA_GAP','cutoff_exclusive':'2026-08-10','source_provider':'Cboe Global Markets','series':meta,'source_errors':errors,'families':fam,'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
    OUT.write_text(json.dumps(p,indent=2,sort_keys=True)+'\n'); print(p['status']); print({k:v['status'] for k,v in fam.items()})
if __name__=='__main__': main()
