import gzip
import unittest

from tools.gate_btc_bybit_derivatives_archive_probe import parse_listing, run


class BybitDerivativesArchiveProbeTests(unittest.TestCase):
    def test_listing_parser_respects_cutoff(self):
        raw = b"BTCUSDT2026-08-05.csv.gz\nBTCUSDT2026-08-06.csv.gz\nBTCUSDT2026-08-07.csv.gz\n"
        self.assertEqual(parse_listing("BTCUSDT", raw, "2026-08-06"), ["2026-08-05", "2026-08-06"])

    def test_historical_archive_is_not_live_feed(self):
        listing = b"BTCUSDT2026-08-05.csv.gz\nBTCUSDT2026-08-06.csv.gz\n"
        archive = gzip.compress(b"timestamp,symbol,side,size,price,tickDirection,trdMatchID,grossValue,homeNotional,foreignNotional\n1700000000,BTCUSDT,Buy,1,100,PlusTick,x,1,1,100\n")

        def fetcher(url):
            return archive if url.endswith(".csv.gz") else listing

        report = run("2026-08-06", ["BTCUSDT"], fetcher=fetcher, max_workers=1)
        self.assertEqual(report["status"], "PASS_HISTORICAL_REDUNDANCY_AVAILABLE")
        self.assertEqual(report["historical_archive_available_count"], 1)
        self.assertFalse(report["live_v5_feed_restored"])
        self.assertFalse(report["engine_feed"])
        self.assertFalse(report["feeds_frozen_engine"])
        self.assertFalse(report["source_substitution_performed"])
        self.assertFalse(report["proxy_or_geo_bypass_used"])
        self.assertEqual(report["methodology_changes"], 0)
        self.assertEqual(report["orders_generated"], 0)
        self.assertEqual(report["real_capital_used"], 0)


if __name__ == "__main__":
    unittest.main()
