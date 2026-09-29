from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools.gate_btc_v2a_coinpaprika_closed_candles import candidate_close, parse_closed


GENESIS = {"first_full_prospective_utc_date": "2026-09-30"}
BINANCE = {"coinpaprika_id": "btc-bitcoin", "symbol": "BTC", "source_identity": "BINANCE_SPOT",
           "source_symbol": "BTCUSDT"}
OKX = {"coinpaprika_id": "sui-sui", "symbol": "SUI", "source_identity": "OKX_SPOT",
       "source_symbol": "SUI-USDT"}
START = 1790726400000  # 2026-09-30T00:00:00Z


class ProspectiveClosedCandlesTests(unittest.TestCase):
    def test_no_pre_genesis_or_same_day_candle(self):
        self.assertIsNone(candidate_close(datetime(2026, 9, 30, 23, 59, tzinfo=timezone.utc), GENESIS))
        self.assertEqual(candidate_close(datetime(2026, 10, 1, 0, 1, tzinfo=timezone.utc), GENESIS).isoformat(), "2026-09-30")

    def test_binance_requires_exact_completed_utc_interval(self):
        from datetime import date
        target = date(2026, 9, 30)
        now = datetime(2026, 10, 1, 1, tzinfo=timezone.utc)
        bar = [START, "1", "2", "0.5", "1.5", "10", START + 86_400_000 - 1, "15"]
        result = parse_closed(BINANCE, [bar], target, now)
        self.assertEqual(result["close_usd"], 1.5)
        with self.assertRaisesRegex(ValueError, "wrong UTC interval"):
            parse_closed(BINANCE, [[START - 86_400_000, *bar[1:]]], target, now)
        with self.assertRaisesRegex(ValueError, "not yet closed"):
            parse_closed(BINANCE, [bar], target, datetime(2026, 9, 30, 20, tzinfo=timezone.utc))

    def test_okx_requires_confirmed_utc_daily_bar(self):
        from datetime import date
        target = date(2026, 9, 30)
        now = datetime(2026, 10, 1, 1, tzinfo=timezone.utc)
        bar = [str(START), "1", "2", "0.5", "1.5", "10", "10", "15", "1"]
        self.assertEqual(parse_closed(OKX, {"code": "0", "data": [bar]}, target, now)["close_usd"], 1.5)
        with self.assertRaisesRegex(ValueError, "confirmed"):
            parse_closed(OKX, {"code": "0", "data": [[*bar[:8], "0"]]}, target, now)


if __name__ == "__main__":
    unittest.main()
