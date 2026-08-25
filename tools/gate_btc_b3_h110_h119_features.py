#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from io import StringIO
import numpy as np,pandas as pd,requests
BASE='https://cdn.cboe.com/api/global/us_indices/daily_prices/'
SYMS=('VIX','VIX9D','VVIX','OVX','GVZ','VXEEM')
CUTOFF=pd.Timestamp('2026-08-10')
def fetch(sym):
 r=requests.get(BASE+f'{sym}_History.csv',timeout=(5,60),headers={'User-Agent':'QRDS-B3-H110-H119/1.0'});r.raise_for_status();raw=r.content;x=pd.read_csv(StringIO(raw.decode('utf-8-sig')));c={k.strip().upper():k for k in x.columns};v=c.get('CLOSE') or c.get(sym)
 if 'DATE' not in c or v is None:raise RuntimeError(f'{sym} bad schema {list(x.columns)}')
 d=pd.DataFrame({'date':pd.to_datetime(x[c['DATE']],errors='coerce'),'value':pd.to_numeric(x[v],errors='coerce')}).dropna().sort_values('date').drop_duplicates('date');d=d[(d.date>='2019-01-01')&(d.date<CUTOFF)].reset_index(drop=True)
 return d,{'provider':'Cboe Global Markets','url':r.url,'raw_sha256':hashlib.sha256(raw).hexdigest(),'rows':len(d),'first':str(d.date.min().date()),'last':str(d.date.max().date()),'value_column':v}
def build():
 series={};meta={};z=None
 for s in SYMS:
  d,meta[s]=fetch(s);series[s]=d;q=d.rename(columns={'value':s});z=q if z is None else z.merge(q,on='date',how='outer')
 z=z.sort_values('date').reset_index(drop=True)
 for s in SYMS:
  z[f'd_{s}']=np.log(z[s]).diff();sc=z[f'd_{s}'].abs().shift(1).rolling(60,min_periods=40).median();z[f'zchg_{s}']=z[f'd_{s}']/sc
  mu=z[s].shift(1).rolling(60,min_periods=40).mean();sd=z[s].shift(1).rolling(60,min_periods=40).std(ddof=0);z[f'zlvl_{s}']=(z[s]-mu)/sd.replace(0,np.nan)
 for n,a,b in [('term','VIX9D','VIX'),('vvix','VVIX','VIX'),('ovx','OVX','VIX'),('gvz','GVZ','VIX'),('vxeem','VXEEM','VIX')]:
  z[n]=z[a]/z[b];d=np.log(z[n]).diff();z[f'{n}_zchg']=d/d.abs().shift(1).rolling(60,min_periods=40).median()
 cols=[f'zlvl_{s}' for s in ('VIX','OVX','GVZ','VXEEM')];z['dispersion']=z[cols].std(axis=1,ddof=0);d=z.dispersion.diff();z['dispersion_zchg']=d/d.abs().shift(1).rolling(60,min_periods=40).median()
 z['stress_mag']=z[[f'zchg_{s}' for s in ('VIX9D','VVIX','OVX','GVZ','VXEEM')]].mean(axis=1);z['stress_sign']=np.sign(z.stress_mag);z['prev_stress_sign']=z.stress_sign.shift(1)
 return z,meta
def map_sessions(feat,sessions):
 l=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))});j=pd.merge_asof(l.sort_values('session'),feat.sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False);age=(j.session-j.date).dt.days;j=j[(age>=1)&(age<=5)];return {r.session.date().isoformat():r for r in j.itertuples()}
