import copy
import hashlib
from datetime import datetime,timedelta,timezone
import gzip
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from tools import gate_btc_system13_native_capture as c

BEGIN=datetime(2026,10,22,tzinfo=timezone.utc)
NOW=BEGIN+timedelta(days=1,hours=5)
TS=int(BEGIN.timestamp())

def payload(venue):
 if venue=='BINANCE_SPOT':return [[TS*1000,'100','110','90','105','20',(TS+86400)*1000-1,'2100']]
 if venue=='OKX_SPOT':return {'code':'0','data':[[str(TS*1000),'100','110','90','105','20','2100','2100','1']]}
 if venue=='GATE_SPOT':return [[str(TS),'2100','105','110','90','100','20','true']]
 if venue=='BITGET_SPOT':return {'code':'00000','data':[[str(TS*1000),'100','110','90','105','20','2100']]}
 if venue=='COINBASE_SPOT':return [[TS,'90','110','100','105','20']]
 if venue=='XT_SPOT':return {'rc':0,'result':[{'t':TS*1000,'o':'100','h':'110','l':'90','c':'105','q':'20','v':'2100'}]}
 return {'error':[],'result':{'XB':[[TS,'100','110','90','105','104','20',3],
  [TS+86400,'105','106','104','105','105','4',1]],'last':TS+86400}}

def ready(n=1):
 return {'protocol_sha256':c.PROTOCOL_SHA256,'observed_panel_sha256':'a'*64,'eligible_members':n,
  'rows':[{'coin_id':'coin'+str(i),'eligible_in_observed_panel':True,'exact_binding_candidate':True,
   'source_identity':'BINANCE_SPOT','source_symbol':'BTCUSDT','literal_quote_unit_candidate':'USDT'} for i in range(n)]}

def metadata():return {'symbols':[{'symbol':'BTCUSDT','baseAsset':'BTC','quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True}]}

class NativeCapture(unittest.TestCase):
 def xt_metadata(self):
  return {'rc':0,'result':{'symbols':[{'symbol':'shfl_usdt','type':'normal','state':'ONLINE',
    'tradingEnabled':True,'openapiEnabled':False,'baseCurrency':'shfl','quoteCurrency':'usdt',
    'chainRelation':[{'contract':c.XT_SHFL_CONTRACT}]}]}}
 def test_xt_contract_is_pinned_and_market_observation_does_not_authorize_orders(self):
  d=self.xt_metadata();self.assertEqual(c.metadata_index('XT_SPOT',d),{'shfl_usdt':('SHFL','USDT')})
  d['result']['symbols'][0]['chainRelation'][0]['contract']='0x'+'0'*40
  self.assertEqual(c.metadata_index('XT_SPOT',d),{})
 def test_new_binding_extends_daily_capture_without_requerying_or_rewriting_parent(self):
  with tempfile.TemporaryDirectory() as td:
   folder=Path(td);calls=[]
   def fetch(url):
    calls.append(url)
    if 'exchangeInfo' in url:d=metadata()
    elif '/public/symbol' in url:d=self.xt_metadata()
    elif '/public/kline' in url:d=payload('XT_SPOT')
    else:d=payload('BINANCE_SPOT')
    return c.encoded(d),NOW
   r=ready();first=c.collect(folder,r,NOW,fetch,lambda _:None)
   parent=folder/'observations'/first['attempt_id']/'RECEIPT.json';before=parent.read_bytes()
   r=ready(2);r['rows'][1].update(source_identity='XT_SPOT',source_symbol='shfl_usdt')
   second=c.collect(folder,r,NOW,fetch,lambda _:None)
   self.assertEqual(len(calls),4);self.assertEqual(second['native_closed_ohlcv_observed_assets'],2)
   self.assertEqual(second['unchanged_rows_reused'],1)
   self.assertEqual(second['parent_attempt_id'],first['attempt_id'])
   self.assertEqual(second['parent_receipt_sha256'],hashlib.sha256(before).hexdigest())
   self.assertEqual(parent.read_bytes(),before)
   self.assertFalse(second['rows'][1]['api_order_capability_qualified'])
   self.assertEqual(second['rows'][1]['volume'],20)
   self.assertFalse(second['source_admitted']);self.assertEqual(second['qualified_system13_ohlcv_assets'],0)
   c.collect(folder,r,NOW,lambda _:self.fail('same binding plan must not retry'),lambda _:None)
 def test_all_venue_adapters_keep_base_volume_not_quote_volume(self):
  for venue in c.METADATA:
   self.assertEqual(c.parse_bar(venue,payload(venue),BEGIN,NOW),{'open':100.,'high':110.,'low':90.,'close':105.,'volume':20.})
 def test_missing_duplicate_unclosed_and_wrong_day_are_rejected(self):
  d=payload('BINANCE_SPOT');d[0][0]+=1
  with self.assertRaisesRegex(ValueError,'MISSING'):c.parse_bar('BINANCE_SPOT',d,BEGIN,NOW)
  d=payload('BINANCE_SPOT')*2
  with self.assertRaisesRegex(ValueError,'DUPLICATED'):c.parse_bar('BINANCE_SPOT',d,BEGIN,NOW)
  d=payload('OKX_SPOT');d['data'][0][8]='0'
  with self.assertRaises(ValueError):c.parse_bar('OKX_SPOT',d,BEGIN,NOW)
  d=payload('GATE_SPOT');d[0][7]='false'
  with self.assertRaises(ValueError):c.parse_bar('GATE_SPOT',d,BEGIN,NOW)
  for now in (BEGIN,NOW+timedelta(days=1)):
   with self.assertRaisesRegex(ValueError,'UNFINISHED_OR_LATE'):c.parse_bar('BITGET_SPOT',payload('BITGET_SPOT'),BEGIN,now)
 def test_kraken_uncommitted_final_row_cannot_become_closed(self):
  d=payload('KRAKEN_SPOT');d['result']['XB']=d['result']['XB'][:1]
  with self.assertRaisesRegex(ValueError,'MISSING'):c.parse_bar('KRAKEN_SPOT',d,BEGIN,NOW)
 def test_bad_ohlc_and_nonfinite_and_negative_volume_fail(self):
  for index,value in [(2,'99'),(3,'106'),(4,'nan'),(5,'-1')]:
   d=payload('BINANCE_SPOT');d[0][index]=value
   with self.assertRaises(ValueError):c.parse_bar('BINANCE_SPOT',d,BEGIN,NOW)
 def test_metadata_requires_literal_active_instrument_and_unit(self):
  d=metadata();self.assertEqual(c.metadata_index('BINANCE_SPOT',d),{'BTCUSDT':('BTC','USDT')})
  d['symbols'][0]['status']='BREAK';self.assertEqual(c.metadata_index('BINANCE_SPOT',d),{})
 def test_identity_denominator_and_paths_are_not_guessed(self):
  r=ready(2);r['rows'][1]['exact_binding_candidate']=False
  self.assertEqual(len(c.make_plan(r)),2)
  for mutate in [lambda r:r['rows'][0].update(coin_id='../escape'),lambda r:r.update(eligible_members=3),lambda r:r['rows'].append(copy.deepcopy(r['rows'][0]))]:
   r=ready();mutate(r)
   with self.assertRaises(ValueError):c.make_plan(r)
 def test_capture_idempotence_missing_members_no_factor_and_no_scientific_credit(self):
  with tempfile.TemporaryDirectory() as td:
   calls=[]
   def fetch(url):
    calls.append(url);return c.encoded(metadata() if 'exchangeInfo' in url else payload('BINANCE_SPOT')),NOW
   r=ready(2);r['rows'][1]['exact_binding_candidate']=False
   folder=Path(td);result=c.collect(folder,r,NOW,fetch,lambda _:None)
   self.assertEqual(len(calls),2);self.assertEqual(result['native_closed_ohlcv_observed_assets'],1)
   self.assertEqual(result['eligible_members'],2);self.assertEqual(result['native_observed_coverage_fraction'],.5)
   row=result['rows'][0];self.assertEqual(row['quote_currency'],'USDT');self.assertIsNone(row['factor'])
   self.assertTrue(row['pre_installation_session_diagnostic_only'])
   self.assertFalse(result['source_admitted']);self.assertFalse(result['training_ready'])
   self.assertEqual(result['qualified_system13_ohlcv_assets'],0);self.assertEqual(result['scientific_credit'],0)
   same=c.collect(folder,r,NOW,lambda _:self.fail('must not retry'),lambda _:None)
   self.assertEqual(same,result)
   evidence=folder/'observations'/result['attempt_id']/result['evidence'][0]['path']
   evidence.write_bytes(gzip.compress(b'changed'))
   with self.assertRaisesRegex(ValueError,'EVIDENCE_MUTATED'):c.collect(folder,r,NOW,fetch,lambda _:None)
 def test_unsupported_bindings_are_explicit_without_network(self):
  with tempfile.TemporaryDirectory() as td:
   r=ready();r['rows'][0]['source_identity']='MXC_SPOT';r['rows'][0]['source_symbol']=None
   d=c.collect(Path(td),r,NOW,lambda _:self.fail('no guessed adapter'),lambda _:None)
   self.assertEqual(d['rows'][0]['status'],'PRIMARY_INSTRUMENT_OR_ADAPTER_UNAVAILABLE')
 def test_rate_limit_stops_venue_and_daily_receipt_prevents_retries(self):
  with tempfile.TemporaryDirectory() as td:
   calls=[]
   def fetch(url):
    calls.append(url)
    if 'exchangeInfo' in url:return c.encoded(metadata()),NOW
    raise HTTPError(url,429,'limited',None,None)
   folder=Path(td);r=ready(3);d=c.collect(folder,r,NOW,fetch,lambda _:None)
   self.assertEqual(len(calls),2)
   self.assertEqual([x['status'] for x in d['rows']],['NATIVE_BAR_UNAVAILABLE','VENUE_RATE_LIMIT_CIRCUIT_OPEN','VENUE_RATE_LIMIT_CIRCUIT_OPEN'])
   c.collect(folder,r,NOW,lambda _:self.fail('retry'),lambda _:None)
 def test_wrong_quote_and_inactive_instrument_cannot_fetch_candles(self):
  with tempfile.TemporaryDirectory() as td:
   r=ready();r['rows'][0]['literal_quote_unit_candidate']='USD'
   def fetch(url):
    self.assertIn('exchangeInfo',url);return c.encoded(metadata()),NOW
   d=c.collect(Path(td),r,NOW,fetch,lambda _:None)
   self.assertEqual(d['rows'][0]['status'],'EXACT_ACTIVE_INSTRUMENT_NOT_CONFIRMED')
 def test_metadata_failure_is_visible_and_keeps_universe(self):
  with tempfile.TemporaryDirectory() as td:
   def fetch(url):return b'not json',NOW
   r=c.collect(Path(td),ready(3),NOW,fetch,lambda _:None)
   self.assertEqual(r['eligible_members'],3);self.assertEqual(r['native_closed_ohlcv_observed_assets'],0)
   self.assertTrue(all(x['status']=='PRIMARY_METADATA_UNAVAILABLE' for x in r['rows']))

if __name__=='__main__':unittest.main()

