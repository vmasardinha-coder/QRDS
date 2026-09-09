from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gate_btc_factory_delta_c2.py"
PREREG = ROOT / "tools" / "gate_btc_factory_delta_c2_prereg.json"


def load_module():
    spec = importlib.util.spec_from_file_location("factory_delta_c2", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DeltaC2Tests(unittest.TestCase):
    def test_prereg_is_frozen_safe_and_materially_distinct(self):
        p = json.loads(PREREG.read_text(encoding="utf-8"))
        self.assertTrue(p["generated_before_results"])
        self.assertEqual(p["issue"], 677)
        self.assertEqual(p["lineage"]["predecessor_result_credit"], 0)
        self.assertEqual(len(p["families"]), 5)
        self.assertEqual(p["historical_cutoff_exclusive"], "2026-08-10")
        self.assertEqual(p["discovery_end_inclusive"], "2026-03-31")
        self.assertEqual(p["replication_start_inclusive"], "2026-04-01")
        self.assertIn("volume", p["source_contract"]["required_fields"])
        self.assertIn("funding_rate", p["source_contract"]["required_fields"])
        self.assertEqual(p["source_contract"]["empiricus_delta_role"], "EXTERNAL_BENCHMARK_ONLY")
        self.assertEqual(p["safety"]["ORDERS"], 0)
        self.assertEqual(p["safety"]["REAL_CAPITAL"], 0)
        self.assertFalse(p["safety"]["ENGINE_FEED"])
        self.assertTrue(p["safety"]["NO_BACKFILL"])
        self.assertTrue(p["safety"]["NO_RETUNE"])
        self.assertTrue(p["safety"]["FAIL_CLOSED"])

    def test_fixture_is_deterministic_and_pipeline_safe(self):
        m = load_module()
        p = m.load_prereg()
        o1, f1 = m.fixture_data()
        o2, f2 = m.fixture_data()
        self.assertEqual(o1.to_csv(index=False), o2.to_csv(index=False))
        self.assertEqual(f1.to_csv(index=False), f2.to_csv(index=False))
        prices, volumes, funding = m.validate_and_panelize(o1, f1, p["historical_cutoff_exclusive"])
        result = m.evaluate(prices, volumes, funding, p)
        self.assertIn(result["status"], {"CLOSED_NULL", "SURVIVORS_READY_FOR_FREEZE"})
        self.assertEqual(result["comparison_capital_brl"], 180000)
        self.assertEqual(result["predecessor_result_credit"], 0)
        self.assertFalse(result["h1_economics_read"])
        self.assertFalse(result["partial_prospective_economics_read"])
        self.assertEqual(result["orders"], 0)
        self.assertEqual(result["real_capital"], 0)
        self.assertFalse(result["engine_feed"])
        self.assertEqual(set(result["families"]), set(p["families"]))
        self.assertLessEqual(len(result["survivors_to_freeze"]), 2)

    def test_future_price_change_cannot_change_past_returns(self):
        m = load_module()
        p = m.load_prereg()
        ohlc, raw_funding = m.fixture_data()
        prices, volumes, funding = m.validate_and_panelize(ohlc, raw_funding, p["historical_cutoff_exclusive"])
        family = "DELTA_C2_FUNDING_DIVERGENCE"
        cfg = p["families"][family]["central"]
        r1, _ = m.run_variant(prices, volumes, funding, family, cfg, p)
        pivot = pd.Timestamp("2026-05-15")
        changed = prices.copy()
        changed.loc[changed.index > pivot] = changed.loc[changed.index > pivot] * 9.0
        r2, _ = m.run_variant(changed, volumes, funding, family, cfg, p)
        pd.testing.assert_series_equal(r1.loc[:pivot], r2.loc[:pivot])

    def test_future_funding_event_is_excluded_by_historical_cutoff(self):
        m = load_module()
        p = m.load_prereg()
        ohlc, raw_funding = m.fixture_data()
        extra = raw_funding.iloc[[0]].copy()
        extra["date"] = pd.Timestamp("2026-08-10")
        extra["funding_time_utc"] = "2026-08-10T00:00:00+00:00"
        extra["funding_rate"] = 99.0
        contaminated = pd.concat([raw_funding, extra], ignore_index=True)
        _prices, _volumes, funding = m.validate_and_panelize(ohlc, contaminated, p["historical_cutoff_exclusive"])
        self.assertLess(funding.index.max(), pd.Timestamp("2026-08-10"))
        self.assertFalse((funding == 99.0).any().any())

    def test_duplicate_funding_event_fails_closed(self):
        m = load_module()
        p = m.load_prereg()
        ohlc, raw_funding = m.fixture_data()
        duplicated = pd.concat([raw_funding, raw_funding.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE_FUNDING_EVENT"):
            m.validate_and_panelize(ohlc, duplicated, p["historical_cutoff_exclusive"])

    def test_no_same_bar_execution(self):
        m = load_module()
        p = m.load_prereg()
        ohlc, raw_funding = m.fixture_data()
        prices, volumes, funding = m.validate_and_panelize(ohlc, raw_funding, p["historical_cutoff_exclusive"])
        family = "DELTA_C2_VOLUME_CONFIRMATION"
        cfg = p["families"][family]["central"]
        rr, audit = m.run_variant(prices, volumes, funding, family, cfg, p)
        first_trade_idx = audit.index[audit["turnover"] > 0]
        self.assertGreater(len(first_trade_idx), 0)
        i = int(first_trade_idx[0])
        # The first rebalance can charge cost at the completed close, but cannot earn that day's return.
        expected_cost_only = -float(p["execution"]["fee_bps_per_turnover_unit"]) / 10000.0 * float(audit.loc[i, "turnover"])
        self.assertAlmostEqual(float(rr.iloc[i]), expected_cost_only, places=12)


if __name__ == "__main__":
    unittest.main()
