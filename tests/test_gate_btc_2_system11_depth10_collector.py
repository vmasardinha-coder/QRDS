import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tools"))
from gate_btc_2_system11_depth10_collector import eligible_book,pair_seconds,okx_spot_feed_class
from unittest.mock import Mock
class T(unittest.TestCase):
 def book(self,p=100):
  return [[p-i,1+i] for i in range(10)],[[p+1+i,1+i] for i in range(10)]
 def test_depth10_and_pairing(self):
  b,a=self.book(); eligible_book(b,a)
  ev=[{"venue":"BINANCE","receipt_ms":1000100,"bids":b,"asks":a},{"venue":"OKX","receipt_ms":1000900,"bids":b,"asks":a}]
  x=pair_seconds(ev);self.assertEqual(len(x),1);self.assertTrue(x[0]["eligible_pair"]);self.assertEqual(len(x[0]["books"]["BINANCE"]["bids"]),10)
 def test_depth1_rejected(self):
  with self.assertRaisesRegex(ValueError,"DEPTH10"): eligible_book([[100,1]],[[101,1]])
 def spot_class(self):
  class Parent:
   id="OKX"
   @classmethod
   def _parse_symbol_data(cls,data):
    return {e["instId"]:e["instId"] for r in data for e in r["data"]}
  return okx_spot_feed_class(Parent,Mock(side_effect=lambda *a,**kw:kw),Mock(side_effect=lambda x:x))
 def test_spot_discovery_is_scoped_and_unwrapped_response_supported(self):
  cls=self.spot_class()
  self.assertEqual(cls.id,"OKX")
  self.assertEqual(cls.rest_endpoints[0]["routes"],["/api/v5/public/instruments?instType=SPOT"])
  response={"code":"0","data":[{"instType":"SPOT","instId":"BTC-USDT"}]}
  self.assertEqual(cls._parse_symbol_data(response),{"BTC-USDT":"BTC-USDT"})
  self.assertEqual(cls._parse_symbol_data([response]),cls._parse_symbol_data(response))
 def test_non_spot_and_api_error_are_fail_closed(self):
  cls=self.spot_class()
  with self.assertRaisesRegex(ValueError,"NON_SPOT"):
   cls._parse_symbol_data({"data":[{"instType":"FUTURES","instId":"MALFORMED"}]})
  with self.assertRaisesRegex(ValueError,"DISCOVERY_ERROR"):
   cls._parse_symbol_data({"code":"500","data":[]})
if __name__=="__main__":unittest.main()
