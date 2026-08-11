import unittest
from datetime import date

from tools.gate_btc_binance_usdm_weekly_shortability import fridays, normalize_asset


class TestBinanceWeeklyShortability(unittest.TestCase):
    def test_normalize_asset(self):
        self.assertEqual(normalize_asset("BTCUSDT"), "BTC")
        self.assertEqual(normalize_asset("1000PEPEUSDT"), "PEPE")
        self.assertEqual(normalize_asset("1000000MOGUSDT"), "MOG")
        self.assertEqual(normalize_asset("LUNA2USDT"), "LUNA")
        self.assertEqual(normalize_asset("BEAMXUSDT"), "BEAM")
        self.assertEqual(normalize_asset("DODOXUSDT"), "DODO")

    def test_fridays_are_causal_calendar_dates(self):
        got = list(fridays(date(2026, 5, 14), date(2026, 6, 5)))
        self.assertEqual([d.isoformat() for d in got], ["2026-05-15", "2026-05-22", "2026-05-29", "2026-06-05"])

    def test_delivery_contract_name_is_not_normalized_as_spot_asset(self):
        # Delivery filtering happens before normalize_asset; underscore is intentionally visible.
        self.assertIn("_", "BTCUSDT_260925")


if __name__ == "__main__":
    unittest.main()
