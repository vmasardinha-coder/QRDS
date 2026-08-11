import unittest
from datetime import date

from tools.gate_btc_binance_usdm_weekly_shortability import day_ms, fridays, normalize_asset


class TestBinanceWeeklyShortability(unittest.TestCase):
    def test_normalize_asset(self):
        self.assertEqual(normalize_asset("BTCUSDT"), "BTC")
        self.assertEqual(normalize_asset("1000PEPEUSDT"), "PEPE")
        self.assertEqual(normalize_asset("1000000MOGUSDT"), "MOG")
        self.assertEqual(normalize_asset("LUNA2USDT"), "LUNA")
        self.assertEqual(normalize_asset("BEAMXUSDT"), "BEAM")

    def test_fridays_are_causal_calendar_dates(self):
        got = list(fridays(date(2026, 5, 14), date(2026, 6, 5)))
        self.assertEqual([d.isoformat() for d in got], ["2026-05-15", "2026-05-22", "2026-05-29", "2026-06-05"])

    def test_day_ms_bounds(self):
        start, end = day_ms(date(2026, 6, 5))
        self.assertEqual(end - start, 86_399_999)


if __name__ == "__main__":
    unittest.main()
