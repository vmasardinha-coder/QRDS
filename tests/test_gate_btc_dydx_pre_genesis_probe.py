import sys
import unittest
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_dydx_pre_genesis_probe as probe


class DydxPreGenesisProbeTests(unittest.TestCase):
    def test_bound_relabels_only_pre_genesis_rows_to_explicit_ethdydx(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2023-10-25", "2023-10-26", "2023-10-27"]),
            "symbol": ["DYDX"] * 3,
            "close_usd": [2.0, 2.1, 2.2],
            "volume_usd": [100.0, 110.0, 120.0],
            "source": ["gateio_usdt"] * 3,
        })
        out = probe.bound_pre_genesis(frame, "gateio_usdt")
        self.assertEqual(out["date"].dt.strftime("%Y-%m-%d").tolist(), ["2023-10-25"])
        self.assertEqual(set(out["symbol"]), {"ETHDYDX"})
        self.assertEqual(set(out["source"]), {"pre_genesis_ethdydx__gateio_usdt"})

    def test_post_genesis_only_data_never_spans_window(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "symbol": ["ETHDYDX"] * 2,
            "close_usd": [2.0, 2.1],
            "volume_usd": [100.0, 110.0],
            "source": ["x", "x"],
        })
        self.assertFalse(probe.spans_historical_snapshot_window(frame))

    def test_full_pre_genesis_window_can_pass(self):
        frame = pd.DataFrame({
            "date": pd.to_datetime(["2021-09-01", "2023-09-30"]),
            "symbol": ["ETHDYDX"] * 2,
            "close_usd": [10.0, 2.0],
            "volume_usd": [100.0, 100.0],
            "source": ["x", "x"],
        })
        self.assertTrue(probe.spans_historical_snapshot_window(frame))

    def test_genesis_boundary_is_frozen(self):
        self.assertEqual(str(probe.CHAIN_GENESIS.date()), "2023-10-26")
        self.assertEqual(str(probe.CMC_LAST_PRE_GENESIS_SNAPSHOT.date()), "2023-09-30")


if __name__ == "__main__":
    unittest.main()
