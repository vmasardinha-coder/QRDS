import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"tools"))
from gate_btc_2_system11_depth10_collector import eligible_book,pair_seconds
class T(unittest.TestCase):
 def book(self,p=100):
  return [[p-i,1+i] for i in range(10)],[[p+1+i,1+i] for i in range(10)]
 def test_depth10_and_pairing(self):
  b,a=self.book(); eligible_book(b,a)
  ev=[{"venue":"BINANCE","receipt_ms":1000100,"bids":b,"asks":a},{"venue":"OKX","receipt_ms":1000900,"bids":b,"asks":a}]
  x=pair_seconds(ev);self.assertEqual(len(x),1);self.assertTrue(x[0]["eligible_pair"]);self.assertEqual(len(x[0]["books"]["BINANCE"]["bids"]),10)
 def test_depth1_rejected(self):
  with self.assertRaisesRegex(ValueError,"DEPTH10"): eligible_book([[100,1]],[[101,1]])
if __name__=="__main__":unittest.main()
