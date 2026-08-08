import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_survivorship_definitive_dydx_segmented_runner as runner


class DydxSegmentedRunnerTests(unittest.TestCase):
    def test_snapshot_segmentation_touches_only_legacy_pre_genesis_slug(self):
        frame = pd.DataFrame([
            {"snapshot_date": "2023-09-30", "rank": 20, "name": "dYdX", "symbol": "DYDX", "cmc_slug": "dydx", "symbol_resolution": "X", "identity_resolved": True},
            {"snapshot_date": "2023-10-31", "rank": 30, "name": "dYdX (ethDYDX)", "symbol": "ETHDYDX", "cmc_slug": "dydxethdydx", "symbol_resolution": "X", "identity_resolved": True},
            {"snapshot_date": "2024-03-31", "rank": 40, "name": "dYdX (Native)", "symbol": "DYDX", "cmc_slug": "dydxchain", "symbol_resolution": "X", "identity_resolved": True},
        ])
        out, touched = runner._segment_snapshots(frame)
        self.assertEqual(len(touched), 1)
        self.assertEqual(out.iloc[0]["symbol"], "DYDXERC20")
        self.assertEqual(out.iloc[1]["symbol"], "ETHDYDX")
        self.assertEqual(out.iloc[2]["symbol"], "DYDX")
        self.assertEqual(out.iloc[0]["symbol_resolution"], "CURATED_DYDX_PRE_GENESIS_SEGMENT")

    def test_bounded_exchange_history_never_crosses_genesis(self):
        raw = pd.DataFrame({
            "date": pd.to_datetime(["2023-10-25", "2023-10-26", "2023-10-27"]),
            "symbol": ["DYDX"] * 3,
            "close_usd": [2.0, 2.1, 2.2],
            "volume_usd": [100.0, 110.0, 120.0],
            "source": ["gateio_usdt"] * 3,
        })
        out = runner._bounded_exchange_history(raw, "gateio")
        self.assertEqual(out["date"].dt.strftime("%Y-%m-%d").tolist(), ["2023-10-25"])
        self.assertEqual(set(out["symbol"]), {"DYDXERC20"})
        self.assertEqual(set(out["source"]), {"gateio_dydx_usdt_pre_genesis_erc20"})

    def test_strict_span_rejects_partial_segment(self):
        partial = pd.DataFrame({
            "date": pd.to_datetime(["2022-01-01", "2023-09-30"]),
            "symbol": ["DYDXERC20"] * 2,
            "close_usd": [5.0, 2.0],
            "volume_usd": [100.0, 100.0],
            "source": ["x", "x"],
        })
        self.assertFalse(runner._strictly_spans_segment(partial, "2021-09-30", "2023-09-30"))

    def test_strict_span_accepts_full_pre_genesis_segment(self):
        full = pd.DataFrame({
            "date": pd.to_datetime(["2021-09-29", "2023-09-30"]),
            "symbol": ["DYDXERC20"] * 2,
            "close_usd": [10.0, 2.0],
            "volume_usd": [100.0, 100.0],
            "source": ["x", "x"],
        })
        self.assertTrue(runner._strictly_spans_segment(full, "2021-09-30", "2023-09-30"))

    def test_identity_audit_blocks_native_and_legacy_until_bounded_recovery(self):
        base = pd.DataFrame([
            {"symbol": "DYDXERC20", "history_usable": True, "exchange_identity_ok": True, "identity_confidence": "BASE", "history_source": "wrong", "history_rows": 100},
            {"symbol": "DYDX", "history_usable": True, "exchange_identity_ok": True, "identity_confidence": "BASE", "history_source": "wrong", "history_rows": 100},
            {"symbol": "ETHDYDX", "history_usable": False, "exchange_identity_ok": True, "identity_confidence": "BASE", "history_source": "", "history_rows": 0},
        ])
        with patch.object(runner, "_ORIGINAL_IDENTITY_AUDIT", return_value=base.copy()):
            out = runner._identity_audit_segmented(pd.DataFrame(), {}, object())
        legacy = out[out.symbol == "DYDXERC20"].iloc[0]
        native = out[out.symbol == "DYDX"].iloc[0]
        eth = out[out.symbol == "ETHDYDX"].iloc[0]
        self.assertFalse(bool(legacy.history_usable))
        self.assertFalse(bool(legacy.exchange_identity_ok))
        self.assertFalse(bool(native.history_usable))
        self.assertFalse(bool(native.exchange_identity_ok))
        self.assertFalse(bool(eth.history_usable))
        self.assertTrue(bool(eth.exchange_identity_ok))

    def test_genesis_and_identity_constants_are_frozen(self):
        self.assertEqual(str(runner.CHAIN_GENESIS.date()), "2023-10-26")
        self.assertEqual(runner.LEGACY_SYMBOL, "DYDXERC20")
        self.assertEqual(runner.LEGACY_CMC_SLUG, "dydx")
        self.assertEqual(runner.NATIVE_CMC_SLUG, "dydxchain")


if __name__ == "__main__":
    unittest.main()
