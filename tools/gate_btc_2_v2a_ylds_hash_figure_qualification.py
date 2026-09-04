#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered YLDS/HASH Figure Markets routes."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
BASE='https://api.figuremarkets.com/public'; UA='QRDS-GateBTC2-ResearchOnly/1'
TARGETS={
 'YLDS':{'coin_id':'ylds','name':'YLDS','quotes':['USD','USDC','USDT']},
 'HASH':{'coin_id':'hash-2','name':'Provenance Blockchain','quotes':['USD']},
}
def get(path,params=None,retries=3):
 u=BASE+path
 if params: u+='?'+urllib.parse.urlencode(params,doseq=True)
 last=None
 for n in range(retries):
  try:
   req=urllib.request.Request(u,headers={'Accept':'application/json','User-Agent':UA})
   with urllib.request.urlopen(req,timeout=60) as r:return u,r.read()
  except Exception as e:last=e;time.sleep(2**n)
 raise RuntimeError(f'Figure request failed: {last}')
def obj(raw): return json.loads(raw.decode())
def select_market(items,symbol,cfg):
 hits=[x for x in items if str(x.get('denom','')).upper()==symbol and str(x.get('quoteDenom','')).upper() in cfg['quotes']]
 if not hits: raise ValueError(f'no exact Figure market for {symbol} in preregistered quote set')
 # HASH collision guard: require Figure unified crypto id/name-like metadata to support Provenance when exposed.
 if symbol=='HASH':
  safe=[]
  for x in hits:
   text=json.dumps(x,sort_keys=True).lower()
   if 'provenance' in text or 'hash-2' in text or x.get('unifiedCryptoassetId') not in (None,''):
    safe.append(x)
  if not safe: raise ValueError('HASH exact Provenance identity not independently supported by Figure market metadata')
  hits=safe
 def rank(x): return (cfg['quotes'].index(str(x.get('quoteDenom')).upper()),str(x.get('symbol')))
 return sorted(hits,key=rank)[0],hits
def parse_dt(s): return datetime.fromisoformat(str(s).replace('Z','+00:00')).astimezone(timezone.utc)
def qualify(symbol,end,out):
 cfg=TARGETS[symbol]; d=out/symbol.lower(); d.mkdir(parents=True,exist_ok=True)
 mu,mr=get('/v1/markets',{'base_asset':symbol,'size':'50','include_hidden':'true'})
 (d/'RAW_MARKETS.json').write_bytes(mr); mo=obj(mr); items=mo.get('data') if isinstance(mo,dict) else None
 if not isinstance(items,list): raise ValueError('unexpected Figure markets envelope')
 market,hits=select_market(items,symbol,cfg); ms=str(market.get('symbol'))
 iu,ir=get('/v1/markets/'+urllib.parse.quote(ms,safe='')); (d/'RAW_MARKET_IDENTITY.json').write_bytes(ir); identity=obj(ir)
 if str(identity.get('symbol'))!=ms or str(identity.get('denom','')).upper()!=symbol or str(identity.get('quoteDenom','')).upper()!=str(market.get('quoteDenom','')).upper(): raise ValueError('Figure market identity mismatch')
 start=end-timedelta(days=32)
 params={'start_date':start.isoformat()+'T00:00:00Z','end_date':end.isoformat()+'T23:59:59Z','interval_in_minutes':'1440','candle_type':'TRADE'}
 cu,cr=get('/v1/markets/'+urllib.parse.quote(ms,safe='')+'/candles',params); (d/'RAW_CANDLES.json').write_bytes(cr); co=obj(cr)
 if not isinstance(co,dict) or not isinstance(co.get('matchHistoryData'),list): raise ValueError('unexpected Figure candle envelope')
 if co.get('symbol') not in (None,ms): raise ValueError('Figure candle symbol mismatch')
 rows=[]
 for x in co['matchHistoryData']:
  dt=parse_dt(x['date']); day=dt.date()
  if day>end: continue
  op,hi,lo,cl=map(float,[x['open'],x['high'],x['low'],x['close']]); vol=float(x['volume'])
  if vol<0: raise ValueError('negative volume')
  if not(lo<=min(op,cl)<=max(op,cl)<=hi): raise ValueError('OHLC invariant failed')
  rows.append({'timestamp':int(dt.timestamp()),'day':day.isoformat(),'open':op,'high':hi,'low':lo,'close':cl,'volume':vol})
 rows.sort(key=lambda x:x['timestamp'])
 if not rows: raise ValueError(f'no {symbol} Figure TRADE daily candles')
 dup=len(rows)-len({x['timestamp'] for x in rows}); mono=all(rows[i]['timestamp']<rows[i+1]['timestamp'] for i in range(len(rows)-1))
 have={x['day'] for x in rows}; first=date.fromisoformat(rows[0]['day']); last=date.fromisoformat(rows[-1]['day']); gaps=[]; cur=first
 while cur<=last:
  if cur.isoformat() not in have:gaps.append(cur.isoformat())
  cur+=timedelta(days=1)
 qa=dup==0 and mono and not gaps and last<=end
 (d/'CANDLES.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in rows))
 return {'symbol':symbol,'coin_id':cfg['coin_id'],'name':cfg['name'],'provider':'FIGURE_MARKETS','market':'SPOT','selected_market':market,'candidate_market_hits':hits,'identity':identity,'rows':len(rows),'earliest_day':rows[0]['day'],'latest_day':rows[-1]['day'],'duplicate_rows':dup,'monotonic':mono,'missing_days_within_returned_interval':gaps,'qa_pass':qa,'status':'QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION' if qa else 'FAIL_CLOSED_FULL_CORPUS_QA','urls':{'markets':mu,'identity':iu,'candles':cu},'sha256':{'markets':hashlib.sha256(mr).hexdigest(),'identity':hashlib.sha256(ir).hexdigest(),'candles':hashlib.sha256(cr).hexdigest()}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--end',default='2026-09-02');ap.add_argument('--output',required=True);a=ap.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True);end=date.fromisoformat(a.end)
 results=[];errors=[]
 for s in ('YLDS','HASH'):
  try:results.append(qualify(s,end,out))
  except Exception as e:errors.append({'symbol':s,'error':str(e),'qa_pass':False,'status':'FAIL_CLOSED_SOURCE_OR_PARSE_ERROR'})
 allr=results+errors; qa=len(results)==2 and all(x.get('qa_pass') for x in results)
 summary={'schema_version':'GATE_BTC_2_V2A_YLDS_HASH_FIGURE_PHYSICAL_V1','requested_end_utc':a.end,'status':'QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION' if qa else 'FAIL_CLOSED_FULL_CORPUS_QA','qa_pass':qa,'results':allr,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True,'qualification_only':True,'source_admitted':False,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'admission_scope':'NONE'}
 (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps(summary,indent=2,sort_keys=True));return 0 if qa else 2
if __name__=='__main__':raise SystemExit(main())
