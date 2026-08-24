#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,time
from io import StringIO
from pathlib import Path
import pandas as pd,requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF=pd.Timestamp('2026-08-10')
FRED={
 'SP500':'SP500',
 'WTI':'DCOILWTICO',
}
FAMILY_REQ={
 'H60':['BRLUSD'],'H61':['SP500'],'H62':['VIX'],'H63':['US10Y'],'H64':['WTI'],
 'H65':['SP500','BRLUSD'],'H66':['SP500','BRLUSD'],'H67':[],
 'H68':['SP500','VIX','BRLUSD','US10Y'],'H69':['SP500','BRLUSD']
}

_ORIG_GET=requests.get
def _bounded_b3_get(url,*args,**kwargs):
 kwargs['timeout']=(5,30)
 return _ORIG_GET(url,*args,**kwargs)
b.requests.get=_bounded_b3_get

def _http_session():
 retry=Retry(total=1,connect=1,read=1,status=1,redirect=2,backoff_factor=.5,
             status_forcelist=(429,500,502,503,504),allowed_methods=frozenset(['GET']))
 s=requests.Session();s.mount('https://',HTTPAdapter(max_retries=retry));return s

def _clean_frame(x,date_col,value_col):
 d=pd.DataFrame({'date':pd.to_datetime(x[date_col],errors='coerce',dayfirst=True),
                 'value':pd.to_numeric(x[value_col].astype(str).str.replace(',','.',regex=False),errors='coerce')})
 d=d.dropna().sort_values('date').drop_duplicates('date')
 d=d[(d.date>=pd.Timestamp('2019-01-01')) & (d.date<CUTOFF)]
 if d.empty: raise ValueError('series empty before cutoff')
 if not d.date.is_monotonic_increasing or d.date.duplicated().any(): raise ValueError('non-monotonic/duplicate dates')
 return d

def _meta(name,provider,url,raw,x,series=None,delivery_path=None):
 return {'name':name,'series':series or name,'provider':provider,'delivery_path':delivery_path or 'official_csv',
         'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(x),
         'first':x.date.min().date().isoformat(),'last':x.date.max().date().isoformat()}

def fetch_bcb_brlusd():
 # Banco Central do Brasil SGS series 1: USD/BRL selling rate, daily, ODbL open data.
 url='https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados'
 params={'formato':'json','dataInicial':'01/01/2019','dataFinal':'09/08/2026'}
 r=_http_session().get(url,params=params,timeout=(5,35),headers={'User-Agent':'QRDS-research/1.0'});r.raise_for_status();raw=r.content
 j=r.json()
 if not isinstance(j,list) or not j: raise ValueError('unexpected/empty BCB JSON')
 x=_clean_frame(pd.DataFrame(j),'data','valor')
 return _meta('BRLUSD','Banco Central do Brasil / SGS',r.url,raw,x,'SGS-1','official_json'),x

def fetch_cboe_vix():
 url='https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv'
 r=_http_session().get(url,timeout=(5,35),headers={'User-Agent':'QRDS-research/1.0'});r.raise_for_status();raw=r.content
 z=pd.read_csv(StringIO(raw.decode('utf-8-sig')))
 cols={c.strip().upper():c for c in z.columns}
 if 'DATE' not in cols or 'CLOSE' not in cols: raise ValueError('unexpected CBOE VIX schema')
 x=_clean_frame(z,cols['DATE'],cols['CLOSE'])
 return _meta('VIX','Cboe Global Markets',r.url,raw,x,'VIX','official_csv'),x

def fetch_treasury_10y():
 frames=[];raw_parts=[];urls=[]
 # Year-partitioned official Treasury CSV avoids deprecated all-history delivery.
 for year in range(2019,2027):
  url=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all'
  params={'type':'daily_treasury_yield_curve','field_tdr_date_value':str(year),'page':'','_format':'csv'}
  r=_http_session().get(url,params=params,timeout=(5,35),headers={'User-Agent':'QRDS-research/1.0'});r.raise_for_status();raw_parts.append(r.content);urls.append(r.url)
  z=pd.read_csv(StringIO(r.content.decode('utf-8-sig')))
  cols={c.strip():c for c in z.columns}
  if 'Date' not in cols or '10 Yr' not in cols: raise ValueError(f'unexpected Treasury schema {year}')
  frames.append(z[[cols['Date'],cols['10 Yr']]].rename(columns={cols['Date']:'Date',cols['10 Yr']:'10 Yr'}))
 raw=b'\n'.join(raw_parts);z=pd.concat(frames,ignore_index=True);x=_clean_frame(z,'Date','10 Yr')
 return _meta('US10Y','U.S. Department of the Treasury',urls[-1],raw,x,'10Y Par Yield','official_yearly_csv'),x

def _parse_fred_csv(raw):
 x=pd.read_csv(StringIO(raw.decode('utf-8-sig')))
 if x.shape[1] < 2: raise ValueError('unexpected FRED CSV schema')
 x=x.iloc[:, :2].copy(); x.columns=['date','value']
 x['date']=pd.to_datetime(x['date'],errors='coerce');x['value']=pd.to_numeric(x['value'],errors='coerce')
 x=x.dropna().sort_values('date').drop_duplicates('date');x=x[(x.date>=pd.Timestamp('2019-01-01')) & (x.date<CUTOFF)]
 if x.empty: raise ValueError('FRED series empty before cutoff')
 return x

def fetch_fred(name,series):
 endpoints=[('fredgraph','https://fred.stlouisfed.org/graph/fredgraph.csv',{'id':series,'cosd':'2019-01-01','coed':'2026-08-09'}),('series_download',f'https://fred.stlouisfed.org/series/{series}/downloaddata/{series}.csv',None)]
 last=None;attempt=0;session=_http_session()
 for round_no in range(2):
  for source_name,url,params in endpoints:
   attempt+=1
   try:
    r=session.get(url,params=params,timeout=(5,25),headers={'User-Agent':'QRDS-research/1.0'});r.raise_for_status();raw=r.content
    if not raw or b'DATE' not in raw[:128].upper(): raise ValueError('unexpected/empty FRED CSV')
    x=_parse_fred_csv(raw);m=_meta(name,'FRED',r.url,raw,x,series,source_name);m['fetch_attempt']=attempt;return m,x
   except Exception as e:last=e
  if round_no==0: time.sleep(2)
 raise last

def session_dates(periods,bar):
 ss,_=b.sample(periods,bar);return pd.DatetimeIndex(pd.to_datetime(sorted(ss.keys())))

def causal_coverage(x,sessions):
 d=x[['date','value']].sort_values('date').copy();left=pd.DataFrame({'session':sessions}).sort_values('session')
 j=pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
 age=(j['session']-j['date']).dt.days;ok=j.value.notna() & age.notna() & (age<=5)
 return float(ok.mean()) if len(j) else 0.0,int(ok.sum()),int(len(j)),int(age.dropna().max()) if age.notna().any() else None

def qualify(meta,x,disc,repl):
 dc,dn,dt,dm=causal_coverage(x,disc);rc,rn,rt,rm=causal_coverage(x,repl)
 meta.update({'status':'PASS' if dc>=.90 and rc>=.90 else 'DATA_GAP_COVERAGE','discovery_join_coverage':dc,'replication_join_coverage':rc,'discovery_join_n':f'{dn}/{dt}','replication_join_n':f'{rn}/{rt}','max_stale_days_discovery':dm,'max_stale_days_replication':rm})
 return meta

def main(out):
 disc=session_dates(['2024_26'],5);repl=session_dates(['2020_22','2022_24'],15);series={};frames={}
 sources={'BRLUSD':fetch_bcb_brlusd,'VIX':fetch_cboe_vix,'US10Y':fetch_treasury_10y}
 for n,fn in sources.items():
  try:meta,x=fn();series[n]=qualify(meta,x,disc,repl);frames[n]=x
  except Exception as e:series[n]={'name':n,'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
 for n,s in FRED.items():
  try:meta,x=fetch_fred(n,s);series[n]=qualify(meta,x,disc,repl);frames[n]=x
  except Exception as e:series[n]={'name':n,'series':s,'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
 fam={}
 for f,req in FAMILY_REQ.items():
  if f=='H67':fam[f]={'status':'DATA_GAP_CALENDAR','reason':'official ex-ante FOMC/Copom calendar adapter not yet bound'};continue
  bad=[r for r in req if series.get(r,{}).get('status')!='PASS'];fam[f]={'status':'DATA_READY' if not bad else 'DATA_GAP','missing_or_failed':bad}
 p={'schema':'gate_btc.b3.h60_h69.data_probe.v2','economics_run':False,'cutoff_exclusive':'2026-08-10','discovery_sessions':len(disc),'replication_sessions':len(repl),'series':series,'families':fam,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
 Path(out).write_text(json.dumps(p,indent=2,sort_keys=True));print(json.dumps(p,indent=2,sort_keys=True))
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--out',required=True);a=q.parse_args();main(a.out)
