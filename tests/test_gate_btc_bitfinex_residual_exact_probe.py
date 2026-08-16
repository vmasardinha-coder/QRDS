import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_bitfinex_residual_exact_probe as probe


class BitfinexResidualExactProbeTests(unittest.TestCase):
    def test_contracts_are_exact_and_never_proxy_btcb_with_btc(self):
        self.assertEqual(probe.CONTRACTS["BCD"], ("tBCDUSD", "tBCDUST"))
        self.assertEqual(probe.CONTRACTS["BTCB"], ("tBTCBUSD", "tBTCBUST"))
        self.assertNotIn("tBTCUSD", probe.CONTRACTS["BTCB"])
        self.assertNotIn("tBTCUST", probe.CONTRACTS["BTCB"])

    def test_aggregate_trades_preserves_target_identity_and_quote_notional(self):
        rows = [
            [1, 1609459200000, 2.0, 10.0],
            [2, 1609462800000, -3.0, 11.0],
            [3, 1609545600000, 4.0, 12.0],
        ]
        out = probe.aggregate_trades(rows, "BCD", "tBCDUSD")
        self.assertEqual(set(out["symbol"]), {"BCD"})
        self.assertEqual(set(out["source"]), {"bitfinex_public_trades_exact_bcdusd"})
        self.assertEqual(out["close_usd"].tolist(), [11.0, 12.0])
        self.assertEqual(out["volume_usd"].tolist(), [53.0, 48.0])

    def test_probe_selects_best_direct_pair_without_relabeling(self):
        usd = pd.DataFrame({
            "date": pd.to_datetime(["2020-01-01", "2020-01-02"]),
            "symbol": ["BCD", "BCD"],
            "close_usd": [1.0, 1.1],
            "volume_usd": [10.0, 11.0],
            "source": ["bitfinex_public_trades_exact_bcdusd"] * 2,
        })
        ust = pd.DataFrame({
            "date": pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]),
            "symbol": ["BCD"] * 3,
            "close_usd": [1.0, 1.1, 1.2],
            "volume_usd": [10.0, 11.0, 12.0],
            "source": ["bitfinex_public_trades_exact_bcdust"] * 3,
        })
        with patch.object(probe, "fetch_pair", side_effect=[
            (usd, "https://example/bcdusd", "PASS_DIRECT_EXACT_PAIR"),
            (ust, "https://example/bcdust", "PASS_DIRECT_EXACT_PAIR"),
        ]):
            best, evidence = probe.probe_symbol(object(), "BCD")
        self.assertEqual(len(best), 3)
        self.assertEqual(set(best["symbol"]), {"BCD"})
        self.assertEqual(len(evidence), 2)
        self.assertTrue(all(row["symbol"] == "BCD" for row in evidence))

    def test_unknown_symbol_is_fail_closed(self):
        out, evidence = probe.probe_symbol(object(), "BTC")
        self.assertTrue(out.empty)
        self.assertEqual(evidence[0]["status"], "BLOCKED_NOT_CURATED")


if __name__ == "__main__":
    unittest.main()
