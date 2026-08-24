#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from io import StringIO
from pathlib import Path
import pandas as pd,requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF=pd.Timestamp('2026-08-10')
FRED={
 'BRLUSD':'DEXBZUS',
 'SP500':'SP500',
 'VIX':'VIXCLS',
 'US10Y':'DGS10',
 'WTI':'DCOILWTICO',
}
FAMILY_REQ={
 'H60':['BRLUSD'],'H61':['SP500'],'H62':['VIX'],'H63':['US10Y'],'H64':['WTI'],
 'H65':['SP500','BRLUSD'],'H66':['SP500','BRLUSD'],'H67':[],
 'H68':['SP500','VIX','BRLUSD','US10Y'],'H69':['SP500','BRLUSD']
}

def _http_session():
 # Deliberately no transport retries here. This QA probes multiple official
 # endpoints and must finish well inside the workflow timeout. A failed path
 # falls through immediately to the second official FRED path, and a complete
 # failure is recorded fail-closed as DATA_GAP_FETCH. This changes delivery
 # mechanics only; observations, cutoff, causal joins, families and economics
 # remain frozen.
 retry=Retry(total=0,connect=0,read=0,status=0,redirect=2,
             allowed_methods=frozenset(['GET']))
 s=requests.Session();s.mount('https://',HTTPAdapter(max_retries=retry));return s

def _parse_fred_csv(raw):
 x=pd.read_csv(StringIO(raw.decode('utf-8-sig')))
 if x.shape[1] < 2: raise ValueError('unexpected FRED CSV schema')
 x=x.iloc[:, :2].copy(); x.columns=['date','value']
 x['date']=pd.to_datetime(x['date'],errors='coerce')
 x['value']=pd.to_numeric(x['value'],errors='coerce')
 x=x.dropna().sort_values('date').drop_duplicates('date')
 x=x[(x.date>=pd.Timestamp('2019-01-01')) & (x.date<CUTOFF)]
 if x.empty: raise ValueError('FRED series empty before cutoff')
 return x

def fetch_fred(name,series):
 # Two official FRED delivery paths; each gets one short bounded attempt.
 endpoints=[
   ('fredgraph','https://fred.stlouisfed.org/graph/fredgraph.csv',{'id':series,'cosd':'2019-01-01','coed':'2026-08-09'}),
   ('series_download',f'https://fred.stlouisfed.org/series/{series}/downloaddata/{series}.csv',None),
 ]
 last=None
 session=_http_session()
 for source_name,url,params in endpoints:
  try:
   r=session.get(url,params=params,timeout=(5,10),headers={'User-Agent':'QRDS-research/1.0'})
   r.raise_for_status();raw=r.content
   if not raw or b'DATE' not in raw[:128].upper(): raise ValueError('unexpected/empty FRED CSV')
   x=_parse_fred_csv(raw)
   return {'name':name,'series':series,'provider':'FRED','delivery_path':source_name,'url':r.url,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(x),'first':x.date.min().date().isoformat(),'last':x.date.max().date().isoformat(),'fetch_attempt':1},x
  except Exception as e:
   last=e
 raise last

def session_dates(periods,bar):
 ss,_=b.sample(periods,bar);return pd.DatetimeIndex(pd.to_datetime(sorted(ss.keys())))

def causal_coverage(x,sessions):
 # strictly prior available observation; never same-day input
 d=x[['date','value']].sort_values('date').copy(); left=pd.DataFrame({'session':sessions}).sort_values('session')
 j=pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
 age=(j['session']-j['date']).dt.days
 ok=j.value.notna() & age.notna() & (age<=5)
 return float(ok.mean()) if len(j) else 0.0,int(ok.sum()),int(len(j)),int(age.dropna().max()) if age.notna().any() else None

def main(out):
 disc=session_dates(['2024_26'],5); repl=session_dates(['2020_22','2022_24'],15)
 series={};frames={}
 for n,s in FRED.items():
  try:
   meta,x=fetch_fred(n,s);dc,dn,dt,dm=causal_coverage(x,disc);rc,rn,rt,rm=causal_coverage(x,repl)
   meta.update({'status':'PASS' if dc>=.90 and rc>=.90 else 'DATA_GAP_COVERAGE','discovery_join_coverage':dc,'replication_join_coverage':rc,'discovery_join_n':f'{dn}/{dt}','replication_join_n':f'{rn}/{rt}','max_stale_days_discovery':dm,'max_stale_days_replication':rm});series[n]=meta;frames[n]=x
  except Exception as e: series[n]={'name':n,'series':s,'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
 fam={}
 for f,req in FAMILY_REQ.items():
  if f=='H67': fam[f]={'status':'DATA_GAP_CALENDAR','reason':'official ex-ante FOMC/Copom calendar adapter not yet bound'};continue
  bad=[r for r in req if series.get(r,{}).get('status')!='PASS'];fam[f]={'status':'DATA_READY' if not bad else 'DATA_GAP','missing_or_failed':bad}
 p={'schema':'gate_btc.b3.h60_h69.data_probe.v1','economics_run':False,'cutoff_exclusive':'2026-08-10','discovery_sessions':len(disc),'replication_sessions':len(repl),'series':series,'families':fam,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
 Path(out).write_text(json.dumps(p,indent=2,sort_keys=True));print(json.dumps(p,indent=2,sort_keys=True))
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--out',required=True);a=q.parse_args();main(a.out)
