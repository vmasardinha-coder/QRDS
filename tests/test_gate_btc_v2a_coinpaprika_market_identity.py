from __future__ import annotations

import unittest
from datetime import datetime, timezone

from tools.gate_btc_v2a_coinpaprika_market_identity import adjudicate, expected_market


NOW = datetime(2026, 9, 29, 19, tzinfo=timezone.utc)
ROW = {"coinpaprika_id": "btc-bitcoin", "symbol": "BTC",
       "qualified_candle_source": "BINANCE_SPOT", "qualified_source_symbol": "BTCUSDT"}
MARKET = {"exchange_id": "binance", "pair": "BTC/USDT", "category": "Spot",
          "base_currency_id": "btc-bitcoin", "quote_currency_id": "usdt-tether",
          "outlier": False, "last_updated": "2026-09-29T18:59:00Z"}


class ExactMarketIdentityTests(unittest.TestCase):
    def test_admits_exact_fresh_provider_id_and_frozen_exchange_instrument(self):
        result = adjudicate(ROW, [MARKET], "hash", NOW)
        self.assertEqual(result["status"], "EXACT_MARKET_IDENTITY_CONFIRMED")
        self.assertEqual(result["base_currency_id"], "btc-bitcoin")

    def test_rejects_same_symbol_but_different_asset_id(self):
        result = adjudicate(ROW, [{**MARKET, "base_currency_id": "btc-other"}], "hash", NOW)
        self.assertEqual(result["status"], "NO_EXACT_SPOT_MARKET")

    def test_rejects_outlier_and_stale_market(self):
        self.assertEqual(adjudicate(ROW, [{**MARKET, "outlier": True}], "hash", NOW)["status"],
                         "NO_EXACT_SPOT_MARKET")
        self.assertEqual(adjudicate(ROW, [{**MARKET, "last_updated": "2026-09-20T00:00:00Z"}],
                                    "hash", NOW)["status"], "STALE_OR_MISSING_MARKET_TIMESTAMP")

    def test_rejects_symbol_only_source_mapping(self):
        self.assertIsNone(expected_market({**ROW, "qualified_source_symbol": "WRONGBTCUSDT"}))


if __name__ == "__main__":
    unittest.main()
