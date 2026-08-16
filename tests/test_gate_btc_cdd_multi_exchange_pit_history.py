import unittest

from tools.gate_btc_cdd_multi_exchange_pit_history import parse_csv


class CDDMultiExchangePITTests(unittest.TestCase):
    def test_parse_usd_quote_volume(self):
        text = "https://www.cryptodatadownload.com\nunix,date,symbol,open,high,low,close,Volume BTC,Volume USD\n1735776000,2025-01-02,BTC/USD,1,3,0.5,2.5,100,250\n"
        frame = parse_csv(text, "BTC", "Gemini", "USD")
        self.assertEqual(len(frame), 1)
        self.assertEqual(float(frame.iloc[0]["close_usd"]), 2.5)
        self.assertEqual(float(frame.iloc[0]["volume_usd"]), 250.0)
        self.assertEqual(frame.iloc[0]["source"], "cryptodatadownload_gemini_usd")

    def test_parse_base_ccy_header_when_filename_fixes_usd_quote(self):
        text = "https://www.cryptodatadownload.com\nunix,date,symbol,open,high,low,close,Volume Crypto,Volume Base Ccy\n1735776000,2025-01-02,TEST/USD,1,3,0.5,2.5,100,250\n"
        frame = parse_csv(text, "TEST", "Bitfinex", "USD")
        self.assertEqual(len(frame), 1)
        self.assertEqual(float(frame.iloc[0]["volume_usd"]), 250.0)


if __name__ == "__main__":
    unittest.main()
