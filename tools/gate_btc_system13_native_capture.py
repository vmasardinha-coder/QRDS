"""Capture native spot daily OHLCV observations. Never admit sources or invent factors."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UTC=timezone.utc
PROTOCOL_SHA256='a8f90a269efd64cd939c8707b23c2db31962cdabf6742b0e97bb016be92e4670'
FIRST_PROSPECTIVE_SESSION='2026-10-24'
XT_SHFL_CONTRACT='0x8881562783028f5c1bcb985d2283d5e170d88888'
METADATA={
 'BINANCE_SPOT':'https://data-api.binance.vision/api/v3/exchangeInfo',
 'OKX_SPOT':'https://www.okx.com/api/v5/public/instruments?instType=SPOT',
 'GATE_SPOT':'https://api.gateio.ws/api/v4/spot/currency_pairs',
 'BITGET_SPOT':'https://api.bitget.com/api/v2/spot/public/symbols',
 'KRAKEN_SPOT':'https://api.kraken.com/0/public/AssetPairs',
 'XT_SPOT':'https://sapi.xt.com/v4/public/symbol?symbols=shfl_usdt',
}


def sha(raw):return hashlib.sha256(raw).hexdigest()
def utc(s):
 d=datetime.fromisoformat(s.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return d.astimezone(UTC)
def encoded(d):return (json.dumps(d,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def write_json(path,d):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(d))


def metadata_index(venue,d):
 """Use literal venue instruments; no coin identity inference or alias guessing."""
 if venue=='BINANCE_SPOT':
  rows=[(x['symbol'],x['baseAsset'],x['quoteAsset']) for x in d['symbols'] if x['status']=='TRADING' and x.get('isSpotTradingAllowed') is True]
 elif venue=='OKX_SPOT':
  if d.get('code')!='0':raise ValueError('EXCHANGE_API_ERROR')
  rows=[(x['instId'],x['baseCcy'],x['quoteCcy']) for x in d['data'] if x['state']=='live' and x['instType']=='SPOT']
 elif venue=='GATE_SPOT':rows=[(x['id'],x['base'],x['quote']) for x in d if x['trade_status']=='tradable']
 elif venue=='BITGET_SPOT':
  if d.get('code')!='00000':raise ValueError('EXCHANGE_API_ERROR')
  rows=[(x['symbol'],x['baseCoin'],x['quoteCoin']) for x in d['data'] if x['status']=='online']
 elif venue=='KRAKEN_SPOT':
  if d.get('error'):raise ValueError('EXCHANGE_API_ERROR')
  rows=[(x['altname'],*x['wsname'].split('/')) for x in d['result'].values() if x.get('status')=='online' and len(x.get('wsname','').split('/'))==2]
 elif venue=='XT_SPOT':
  if d.get('rc')!=0:raise ValueError('EXCHANGE_API_ERROR')
  rows=[(x['symbol'],x['baseCurrency'].upper(),x['quoteCurrency'].upper())
        for x in d['result']['symbols'] if x['symbol']=='shfl_usdt' and x.get('type')=='normal'
        and x.get('state')=='ONLINE' and x.get('tradingEnabled') is True
        and any(r.get('contract','').lower()==XT_SHFL_CONTRACT for r in x.get('chainRelation',[]))]
 else:raise ValueError('UNSUPPORTED_VENUE')
 result={}
 for instrument,base,quote in rows:
  if instrument in result and result[instrument]!=(base,quote):raise ValueError('AMBIGUOUS_PRIMARY_INSTRUMENT')
  result[instrument]=(base,quote)
 return result


def candle_url(venue,instrument,begin):
 start=int(begin.timestamp())
 if venue=='BINANCE_SPOT':return 'https://data-api.binance.vision/api/v3/klines?'+urlencode({'symbol':instrument,'interval':'1d','timeZone':'0','startTime':start*1000,'endTime':(start+86400)*1000-1,'limit':2})
 if venue=='OKX_SPOT':return 'https://www.okx.com/api/v5/market/candles?'+urlencode({'instId':instrument,'bar':'1Dutc','limit':3})
 if venue=='GATE_SPOT':return 'https://api.gateio.ws/api/v4/spot/candlesticks?'+urlencode({'currency_pair':instrument,'interval':'1d','from':start,'to':start+86399})
 if venue=='BITGET_SPOT':return 'https://api.bitget.com/api/v2/spot/market/candles?'+urlencode({'symbol':instrument,'granularity':'1Dutc','limit':3})
 if venue=='KRAKEN_SPOT':return 'https://api.kraken.com/0/public/OHLC?'+urlencode({'pair':instrument,'interval':1440,'since':start})
 if venue=='XT_SPOT':return 'https://sapi.xt.com/v4/public/kline?'+urlencode({'symbol':instrument,'interval':'1d','limit':3})
 raise ValueError('UNSUPPORTED_VENUE')


def parse_bar(venue,d,begin,captured):
 if begin.time().isoformat()!='00:00:00':raise ValueError('EXACT_UTC_DAILY_INTERVAL_REQUIRED')
 end=begin+timedelta(days=1)
 if not end<=captured<end+timedelta(days=1):raise ValueError('UNFINISHED_OR_LATE_BAR')
 target=int(begin.timestamp());rows=[]
 if venue=='BINANCE_SPOT':
  for r in d:
   if int(r[0])==target*1000 and int(r[6])==(target+86400)*1000-1:rows.append([r[i] for i in (1,2,3,4,5)])
 elif venue=='OKX_SPOT':
  if d.get('code')!='0':raise ValueError('EXCHANGE_API_ERROR')
  rows=[[r[i] for i in (1,2,3,4,5)] for r in d['data'] if int(r[0])==target*1000 and r[8]=='1']
 elif venue=='GATE_SPOT':
  rows=[[r[i] for i in (5,3,4,2,6)] for r in d if int(r[0])==target and r[7] in ('true',True)]
 elif venue=='BITGET_SPOT':
  if d.get('code')!='00000':raise ValueError('EXCHANGE_API_ERROR')
  rows=[[r[i] for i in (1,2,3,4,5)] for r in d['data'] if int(r[0])==target*1000]
 elif venue=='KRAKEN_SPOT':
  if d.get('error'):raise ValueError('EXCHANGE_API_ERROR')
  series=[v for k,v in d['result'].items() if k!='last']
  if len(series)!=1:raise ValueError('AMBIGUOUS_CANDLE_SERIES')
  # Kraken always includes the current uncommitted candle as the final row.
  rows=[[r[i] for i in (1,2,3,4,6)] for r in series[0][:-1] if int(r[0])==target]
 elif venue=='XT_SPOT':
  if d.get('rc')!=0:raise ValueError('EXCHANGE_API_ERROR')
  # XT q is asset quantity; v is quote turnover and cannot substitute for q.
  rows=[[r[k] for k in ('o','h','l','c','q')] for r in d['result'] if int(r['t'])==target*1000]
 if len(rows)!=1:raise ValueError('EXACT_CLOSED_BAR_MISSING_OR_DUPLICATED')
 values=dict(zip(('open','high','low','close','volume'),map(float,rows[0])))
 if any(not math.isfinite(v) for v in values.values()):raise ValueError('NONFINITE_OHLCV')
 o,h,l,c,v=(values[k] for k in ('open','high','low','close','volume'))
 if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or l>h or v<0:raise ValueError('INVALID_NATIVE_OHLCV')
 return values


def fetch(url):
 # Fixed public URLs only, no credentials, no retries or user-controlled hosts.
 with urlopen(Request(url,headers={'User-Agent':'QRDS-System13-Research/1.0','Accept':'application/json'}),timeout=20) as response:
  raw=response.read(32*1024*1024+1)
  if len(raw)>32*1024*1024:raise ValueError('RESPONSE_TOO_LARGE')
  return raw,datetime.now(UTC)


def make_plan(readiness):
 if readiness.get('protocol_sha256')!=PROTOCOL_SHA256:raise ValueError('SYSTEM13_PROTOCOL_MISMATCH')
 seen=set();plan=[]
 for r in readiness['rows']:
  coin=r['coin_id']
  if coin in seen:raise ValueError('DUPLICATE_MEMBER_IDENTITY')
  seen.add(coin)
  if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]*',coin):raise ValueError('UNSAFE_COIN_ID')
  if r['eligible_in_observed_panel'] is not True:continue
  plan.append({'coin_id':coin,'source_identity':r.get('source_identity'),
    'source_symbol':r.get('source_symbol'),'quote_currency':r.get('literal_quote_unit_candidate'),
    'exact_binding_candidate':r.get('exact_binding_candidate') is True})
 if len(plan)!=readiness['eligible_members']:raise ValueError('OBSERVED_DENOMINATOR_MISMATCH')
 return sorted(plan,key=lambda r:r['coin_id'])


def verified_receipt(attempt):
 result=json.loads((attempt/'RECEIPT.json').read_text())
 if sha((attempt/'INPUT_SOURCE_READINESS.json').read_bytes())!=result['input_readiness_sha256']:
  raise ValueError('CAPTURE_INPUT_MUTATED')
 for proof in result['evidence']:
  path=(attempt/proof['path']).resolve()
  if not path.is_relative_to(attempt.resolve()):raise ValueError('CAPTURE_PATH_OUTSIDE_BUNDLE')
  if sha(gzip.decompress(path.read_bytes()))!=proof['raw_sha256']:raise ValueError('CAPTURE_EVIDENCE_MUTATED')
 return result


def collect(folder,readiness,now=None,fetcher=fetch,pause=time.sleep):
 now=now or datetime.now(UTC)
 if now.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 now=now.astimezone(UTC);begin=now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(days=1)
 plan=make_plan(readiness);panel_hash=readiness['observed_panel_sha256']
 if not re.fullmatch('[a-f0-9]{64}',panel_hash):raise ValueError('INVALID_PANEL_HASH')
 plan_hash=sha(encoded(plan))
 key=now.date().isoformat()+'_'+panel_hash[:16]+'_'+plan_hash[:12];attempt=folder/'observations'/key
 attempt.mkdir(parents=True,exist_ok=True)
 receipt=attempt/'RECEIPT.json'
 if receipt.exists():
  result=verified_receipt(attempt)
  # Failures are explicit and cached too; daily scheduling cannot hammer a bad token.
  if result['observed_panel_sha256']!=panel_hash:raise ValueError('CAPTURE_PANEL_HASH_MISMATCH')
  write_json(folder/'STATUS.json',result)
  return result
 input_path=attempt/'INPUT_SOURCE_READINESS.json'
 if not input_path.exists():write_json(input_path,readiness)
 input_raw=input_path.read_bytes();original=json.loads(input_raw)
 if original['observed_panel_sha256']!=panel_hash:raise ValueError('CAPTURE_INPUT_CHANGED')
 plan=make_plan(original)
 evidence=[];results={};parent_id=None;parent_sha=None
 status_path=folder/'STATUS.json'
 if status_path.exists():
  previous=json.loads(status_path.read_text())
  if (previous.get('capture_date_utc')==now.date().isoformat()
      and previous.get('observed_panel_sha256')==panel_hash
      and previous.get('session')==begin.date().isoformat()):
   parent_id=previous['attempt_id']
   if not re.fullmatch('[a-zA-Z0-9_-]+',parent_id):raise ValueError('UNSAFE_PARENT_CAPTURE_ID')
   parent=folder/'observations'/parent_id;previous=verified_receipt(parent)
   parent_sha=sha((parent/'RECEIPT.json').read_bytes())
   old_plan={r['coin_id']:r for r in make_plan(json.loads((parent/'INPUT_SOURCE_READINESS.json').read_text()))}
   old_rows={r['coin_id']:r for r in previous['rows']}
   for r in plan:
    if old_plan.get(r['coin_id'])==r:results[r['coin_id']]=old_rows[r['coin_id']]
   for proof in previous['evidence']:
    source=parent/proof['path'];destination=attempt/proof['path']
    destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.exists():shutil.copyfile(source,destination)
    if sha(gzip.decompress(destination.read_bytes()))!=proof['raw_sha256']:raise ValueError('CAPTURE_EVIDENCE_MUTATED')
    sidecar=source.with_suffix('.receipt.json')
    if sidecar.exists() and not destination.with_suffix('.receipt.json').exists():shutil.copyfile(sidecar,destination.with_suffix('.receipt.json'))
    evidence.append(proof)
 def get(url,name):
  path=attempt/'raw'/(name+'.json.gz');meta=path.with_suffix('.receipt.json')
  if path.exists() and meta.exists():
   proof=json.loads(meta.read_text());raw=gzip.decompress(path.read_bytes())
   if proof['url']!=url:raise ValueError('CAPTURE_URL_CHANGED')
   if sha(raw)!=proof['raw_sha256']:raise ValueError('CAPTURE_EVIDENCE_MUTATED')
   captured=utc(proof['captured_at_utc'])
  else:
   raw,captured=fetcher(url);proof={'url':url,'path':str(path.relative_to(attempt)),
     'captured_at_utc':captured.isoformat(),'raw_sha256':sha(raw)}
   path.parent.mkdir(exist_ok=True);path.write_bytes(gzip.compress(raw,mtime=0));write_json(meta,proof)
  evidence.append(proof)
  return json.loads(raw),captured,proof
 def venue_work(venue,items):
  local={}
  try:metadata,metadata_at,mp=get(METADATA[venue],venue+'_metadata');index=metadata_index(venue,metadata)
  except Exception as error:
   for r in items:local[r['coin_id']]={**r,'status':'PRIMARY_METADATA_UNAVAILABLE','error':type(error).__name__+':'+str(error)[:180]}
   return local
  circuit_open=False
  for r in items:
   coin=r['coin_id'];instrument=r['source_symbol'];base_quote=index.get(instrument)
   if circuit_open:local[coin]={**r,'status':'VENUE_RATE_LIMIT_CIRCUIT_OPEN'};continue
   if not base_quote or base_quote[1]!=r['quote_currency']:
    local[coin]={**r,'status':'EXACT_ACTIVE_INSTRUMENT_NOT_CONFIRMED'};continue
   try:
    pause(1.1 if venue=='KRAKEN_SPOT' else .4)
    url=candle_url(venue,instrument,begin);d,captured,proof=get(url,coin+'_candles')
    values=parse_bar(venue,d,begin,captured)
    local[coin]={**r,**values,'status':'NATIVE_CLOSED_OHLCV_OBSERVED_UNQUALIFIED',
      'schema':'qrds.system13.observed_native_ohlcv.v1','open_at_utc':begin.isoformat(),
      'close_at_utc':(begin+timedelta(days=1)).isoformat(),'captured_at_utc':captured.isoformat(),
      'base_currency':base_quote[0],'volume_unit':'BASE_ASSET','factor':None,
      'api_order_capability_qualified':False,
      'raw_sha256':proof['raw_sha256'],'metadata_sha256':mp['raw_sha256'],
      'metadata_observed_at_utc':metadata_at.isoformat(),
      'pre_installation_session_diagnostic_only':begin.date().isoformat()<FIRST_PROSPECTIVE_SESSION,
      'source_admitted':False,'adjustment_evidence_qualified':False,'training_eligible':False}
   except Exception as error:
    if getattr(error,'code',None) in (418,429):circuit_open=True
    local[coin]={**r,'status':'NATIVE_BAR_UNAVAILABLE','error':type(error).__name__+':'+str(error)[:180]}
  return local
 groups={}
 for r in plan:
  if r['coin_id'] in results:continue
  if not r['exact_binding_candidate']:results[r['coin_id']]={**r,'status':'EXACT_IDENTITY_MISSING'}
  elif r['source_identity'] not in METADATA or not r['source_symbol']:
   results[r['coin_id']]={**r,'status':'PRIMARY_INSTRUMENT_OR_ADAPTER_UNAVAILABLE'}
  else:groups.setdefault(r['source_identity'],[]).append(r)
 # One sequential worker per venue; bounded requests, no cross-venue symbol fallback.
 reused=len(results)
 with ThreadPoolExecutor(max_workers=6) as executor:
  futures=[executor.submit(venue_work,v,items) for v,items in groups.items()]
  for future in futures:results.update(future.result())
 rows=[results[r['coin_id']] for r in plan];valid=sum(r['status']=='NATIVE_CLOSED_OHLCV_OBSERVED_UNQUALIFIED' for r in rows)
 result={'schema':'qrds.system13.native_capture.v1','status':'NATIVE_CAPTURE_OBSERVED_SOURCE_QUALIFICATION_PENDING',
  'protocol_sha256':PROTOCOL_SHA256,'observed_panel_sha256':panel_hash,
  'input_readiness_sha256':sha(input_raw),'attempt_id':key,'capture_date_utc':now.date().isoformat(),
  'binding_plan_sha256':plan_hash,'parent_attempt_id':parent_id,'parent_receipt_sha256':parent_sha,
  'unchanged_rows_reused':reused if parent_id else 0,
  'session':begin.date().isoformat(),'first_potential_prospective_session':FIRST_PROSPECTIVE_SESSION,
  'eligible_members':len(plan),'native_closed_ohlcv_observed_assets':valid,
  'native_observed_coverage_fraction':valid/len(plan) if plan else 0,
  'missing_or_unavailable_assets':len(plan)-valid,
  'qualified_system13_ohlcv_assets':0,'factor_policy':'MISSING_NO_CONSTANT_OR_ADJUSTMENT_ASSUMPTION',
  'source_admitted':False,'training_ready':False,'holdout_read_allowed':False,'scientific_credit':0,
  'engine_feed':False,'orders':0,'real_capital':0,'evidence':sorted(evidence,key=lambda r:r['path']),
  'rows':rows,'blockers':['SOURCE_SPECIFIC_ADMISSION_REQUIRED','CORPORATE_ACTION_AND_ADJUSTMENT_FACTOR_EVIDENCE_REQUIRED',
    'QUALIFIED_BAR_COVERAGE_AND_CHRONOLOGICAL_PARTITIONS_REQUIRED']}
 write_json(receipt,result);write_json(folder/'STATUS.json',result)
 return result


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--readiness',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=collect(a.out,json.loads(a.readiness.read_text()))
 print(json.dumps({k:v for k,v in r.items() if k not in ('rows','evidence')},sort_keys=True))
