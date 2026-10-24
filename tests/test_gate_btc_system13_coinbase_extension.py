import copy,json,sys,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import gate_btc_system13_native_capture as n
import gate_btc_system13_source_readiness as r

class ExtensionTests(unittest.TestCase):
 def discovery(self):return json.loads((ROOT/'tools/gate_btc_factory/SYSTEM13_EXACT_IDENTITY_EXTENSION_20261024.json').read_text())
 def test_exact_provider_id_and_case_sensitive_solana_mint(self):
  d=self.discovery();self.assertEqual(set(r.discovery_bindings(d)),{'irys','meta-2-2'})
  meta=next(x for x in d['entries'] if x['coin_id']=='meta-2-2')['bindings'][0]
  meta['venue_contract']=meta['venue_contract'].lower()
  with self.assertRaisesRegex(ValueError,'SOLANA_MINT'):r.discovery_bindings(d)
 def test_provider_alias_cannot_replace_observed_id(self):
  d=self.discovery();b=next(x for x in d['entries'] if x['coin_id']=='meta-2-2')['bindings'][0];b['provider_coin_id']='meta-2'
  with self.assertRaisesRegex(ValueError,'SOLANA_MINT'):r.discovery_bindings(d)
 def test_coinbase_metadata_requires_online_and_enabled(self):
  row={'id':'META-USD','base_currency':'META','quote_currency':'USD','status':'online','trading_disabled':False}
  self.assertEqual(n.metadata_index('COINBASE_SPOT',[row]),{'META-USD':('META','USD')})
  row['trading_disabled']=True;self.assertEqual(n.metadata_index('COINBASE_SPOT',[row]),{})
 def test_coinbase_utc_bar_fields_and_base_volume(self):
  at=datetime(2026,10,23,tzinfo=timezone.utc);stamp=int(at.timestamp())
  row=[stamp,95,105,100,102,12]
  bar=n.parse_bar('COINBASE_SPOT',[row],at,at+timedelta(days=1,hours=1))
  self.assertEqual(bar,{'open':100.,'high':105.,'low':95.,'close':102.,'volume':12.})
  with self.assertRaisesRegex(ValueError,'UNFINISHED'):n.parse_bar('COINBASE_SPOT',[row],at,at+timedelta(hours=23))
  with self.assertRaisesRegex(ValueError,'DUPLICATED'):n.parse_bar('COINBASE_SPOT',[row,row],at,at+timedelta(days=1,hours=1))

if __name__=='__main__':unittest.main()
