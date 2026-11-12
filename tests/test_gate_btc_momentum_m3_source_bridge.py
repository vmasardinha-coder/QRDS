import json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from tools import gate_btc_momentum_required_prices as p

CUT='2026-11-11'; AT=datetime(2026,11,12,12,tzinfo=timezone.utc)
class Response:
 def __init__(self,payload):self.payload=payload;self.url='https://example/public';self.status_code=200;self.content=json.dumps(payload).encode()
 def json(self):return self.payload
 def raise_for_status(self):pass
class Session:
 def __init__(self,identity=None,candle=None):self.identity=identity or dict(instId='LEO-USDT',instType='SPOT',baseCcy='LEO',quoteCcy='USDT',state='live');self.candle=candle or [int(datetime(2026,11,11,tzinfo=timezone.utc).timestamp()*1000),'1','2','1','1.5','1','1','1','1']
 def get(self,url,**kw):return Response({'code':'0','data':[self.identity if url.endswith('instruments') else self.candle]})
 def post(self,url,**kw):return Response({'result':'physical_source'})
class SourceBridgeTests(unittest.TestCase):
 def test_seven_new_routes_are_cutoff_bound_and_exact(self):
  ids={'A7A5':'a7a5','GHO':'gho','HASH':'hash-2','REUSD':'re-protocol-reusd','USDGO':'usdgo','USX':'usx','USYC':'hashnote-usyc'}
  for sym,coin in ids.items():
   self.assertIsNone(p.economic_coin_id(sym,'2026-11-10'))
   self.assertEqual(p.economic_coin_id(sym,CUT),coin)
   with patch('tools.gate_btc_pit150_qualified_history.collect_history',return_value=([dict(date=CUT,symbol=sym,close_usd=2)],dict(symbol=sym,coin_id=coin,cutoff=CUT,source='qualified'))):
    self.assertEqual(p.fetch_qualified_economic_close(None,sym,CUT,AT)[0],2)
 def test_post_archives_response_and_request(self):
  r=p.RecordingSession(Session(),lambda:AT);r.post('https://example/public',json={'method':'eth_getLogs'})
  self.assertEqual(r.records[0]['method'],'POST');self.assertEqual(r.records[0]['request_json'],{'method':'eth_getLogs'})
  self.assertEqual(r.records[0]['raw_sha256'],p.sha(json.dumps({'result':'physical_source'}).encode()))
 def test_leo_confirmed_pinned_spot(self):
  self.assertEqual(p.choose_quote(p.fetch_okx_leo_utc_close(Session(),'LEO',CUT),'LEO',CUT),1.5)
 def test_leo_rejects_inactive_wrong_pair_unconfirmed_and_wrong_day(self):
  for key,value in [('instId','FAKE-USDT'),('baseCcy','OTHER'),('quoteCcy','USD'),('state','suspend')]:
   session=Session();session.identity[key]=value
   with self.assertRaisesRegex(ValueError,'IDENTITY_MISMATCH'):p.fetch_okx_leo_utc_close(session,'LEO',CUT)
  session=Session();session.candle[8]='0'
  with self.assertRaisesRegex(ValueError,'NOT_CONFIRMED'):p.fetch_okx_leo_utc_close(session,'LEO',CUT)
  with self.assertRaisesRegex(ValueError,'NOT_EFFECTIVE'):p.fetch_okx_leo_utc_close(Session(),'LEO','2026-11-10')
  session=Session();session.candle[0]+=86400000
  with self.assertRaisesRegex(ValueError,'MISSING_OR_INVALID'):p.fetch_okx_leo_utc_close(session,'LEO',CUT)

if __name__=='__main__':unittest.main()
