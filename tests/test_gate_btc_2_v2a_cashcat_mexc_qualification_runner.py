import json, unittest
from tools.gate_btc_2_v2a_cashcat_mexc_qualification_runner import parse_info, parse
class TestCashcatMexc(unittest.TestCase):
    def test_identity(self): self.assertEqual(parse_info(json.dumps({"symbols":[{"symbol":"CASHCATUSDT","baseAsset":"CASHCAT","quoteAsset":"USDT"}]}).encode())["symbol"],"CASHCATUSDT")
    def test_identity_mismatch(self):
        with self.assertRaises(ValueError): parse_info(json.dumps({"symbols":[{"symbol":"CASHCATUSDT","baseAsset":"OTHER","quoteAsset":"USDT"}]}).encode())
    def test_kline(self): self.assertEqual(parse(json.dumps([[1704067200000,"1","2","0.5","1.5","10",0,"15"]]).encode())[0]["day"],"2024-01-01")
    def test_bad_ohlc(self):
        with self.assertRaises(ValueError): parse(json.dumps([[1704067200000,"1","0.8","0.5","1.5","10"]]).encode())
if __name__=="__main__": unittest.main()
