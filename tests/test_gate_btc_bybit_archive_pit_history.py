import gzip
import unittest

from tools.gate_btc_bybit_archive_pit_history import parse_trade_archive


class BybitArchivePITTests(unittest.TestCase):
    def test_trade_archive_aggregates_daily_close_and_notional(self):
        text = (
            "id,timestamp,price,volume,side,rpi\n"
            "1,1735776000,2.0,3.0,Buy,0\n"
            "2,1735779600,2.5,4.0,Sell,0\n"
            "3,1735862400,3.0,2.0,Buy,0\n"
        )
        frame = parse_trade_archive(gzip.compress(text.encode("utf-8")), "TEST")
        self.assertEqual(len(frame), 2)
        first = frame.iloc[0]
        second = frame.iloc[1]
        self.assertEqual(first["date"].date().isoformat(), "2025-01-02")
        self.assertAlmostEqual(float(first["close_usd"]), 2.5)
        self.assertAlmostEqual(float(first["volume_usd"]), 16.0)
        self.assertEqual(second["date"].date().isoformat(), "2025-01-03")
        self.assertAlmostEqual(float(second["close_usd"]), 3.0)
        self.assertAlmostEqual(float(second["volume_usd"]), 6.0)
        self.assertEqual(first["source"], "bybit_public_spot_archive_usdt")

    def test_trade_archive_requires_price_volume_timestamp(self):
        text = "id,timestamp,price\n1,1735776000,2.0\n"
        with self.assertRaises(ValueError):
            parse_trade_archive(gzip.compress(text.encode("utf-8")), "TEST")


if __name__ == "__main__":
    unittest.main()
