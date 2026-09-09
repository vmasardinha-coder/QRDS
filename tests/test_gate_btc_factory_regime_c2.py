from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "tools" / "gate_btc_factory_regime_c2.py"

spec = importlib.util.spec_from_file_location("regime_c2", MOD_PATH)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RegimeC2Tests(unittest.TestCase):
    def setUp(self):
        self.prereg, self.clarify = m.load_contract()
        self.raw = m.fixture_inputs()
        self.prices = m.panelize(self.raw, self.prereg)

    def test_prereg_is_safe_frozen_and_materially_distinct(self):
        p = self.prereg
        self.assertTrue(p["generated_before_results"])
        self.assertEqual(p["predecessor_result_credit"], 0)
        self.assertTrue(p["source_contract"]["funding_forbidden"])
        self.assertTrue(p["source_contract"]["fred_macro_forbidden"])
        self.assertTrue(p["source_contract"]["new_external_sources_forbidden"])
        self.assertEqual(set(p["families"]), {
            "REGIME_C2_CORRELATION_STRUCTURE",
            "REGIME_C2_RELATIVE_STRENGTH_BREADTH",
            "REGIME_C2_DOWNSIDE_PARTICIPATION",
            "REGIME_C2_SHOCK_RECOVERY",
        })
        self.assertTrue(self.clarify["clarifications_only_no_parameter_change"])
        self.assertEqual(p["safety"]["ORDERS"], 0)
        self.assertEqual(p["safety"]["REAL_CAPITAL"], 0)
        self.assertFalse(p["safety"]["ENGINE_FEED"])

    def test_fixture_is_deterministic_and_pipeline_safe(self):
        a = m.evaluate(self.prices, self.prereg)
        b = m.evaluate(self.prices, self.prereg)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertIn(a["status"], {"CLOSED_NULL", "SURVIVORS_READY_FOR_FREEZE"})
        self.assertLessEqual(len(a["survivors_to_freeze"]), 2)
        self.assertEqual(a["predecessor_result_credit"], 0)
        self.assertFalse(a["h1_economics_read"])
        self.assertFalse(a["partial_prospective_economics_read"])
        self.assertEqual(a["orders"], 0)
        self.assertEqual(a["real_capital"], 0)
        self.assertFalse(a["engine_feed"])

    def test_duplicate_date_symbol_fails_closed(self):
        bad = pd.concat([self.raw, self.raw.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(RuntimeError, "DUPLICATE_DATE_SYMBOL"):
            m.panelize(bad, self.prereg)

    def test_no_same_bar_execution(self):
        idx = pd.date_range("2026-01-01", periods=4, freq="D")
        prices = pd.DataFrame({"BTC": [100.0, 100.0, 100.0, 100.0], "ALT": [100.0, 110.0, 121.0, 133.1]}, index=idx)
        state = pd.Series([0.0, 1.0, 1.0, 1.0], index=idx)
        rr = m.strategy_returns(prices, state, 0.0)
        # State becomes risk-on at day 2 close, therefore day 2 return still uses prior risk-off state.
        self.assertAlmostEqual(float(rr.iloc[1]), 0.0, places=12)
        self.assertAlmostEqual(float(rr.iloc[2]), 0.10, places=12)

    def test_future_price_change_cannot_change_past_family_state_or_returns(self):
        family = "REGIME_C2_RELATIVE_STRENGTH_BREADTH"
        cfg = self.prereg["families"][family]["central"]
        anchor = pd.Timestamp("2026-05-15")
        s1 = m.family_state(self.prices, family, cfg)
        r1 = m.strategy_returns(self.prices, s1, 10.0)
        altered = self.prices.copy()
        altered.loc[altered.index > anchor, altered.columns != "BTC"] *= 7.0
        s2 = m.family_state(altered, family, cfg)
        r2 = m.strategy_returns(altered, s2, 10.0)
        pd.testing.assert_series_equal(s1.loc[:anchor], s2.loc[:anchor])
        pd.testing.assert_series_equal(r1.loc[:anchor], r2.loc[:anchor])

    def test_shock_has_priority_over_simultaneous_recovery(self):
        idx = pd.date_range("2026-01-01", periods=8, freq="D")
        prices = pd.DataFrame({
            "BTC": [100, 100, 100, 100, 100, 90, 90, 90],
            "A": [100, 100, 100, 100, 100, 110, 115, 120],
            "B": [100, 100, 100, 100, 100, 112, 117, 122],
        }, index=idx, dtype=float)
        cfg = {"shock_window": 5, "shock_threshold": -0.08, "recovery_window": 5, "recovery_threshold": 0.04}
        state = m.family_state(prices, "REGIME_C2_SHOCK_RECOVERY", cfg)
        # On day 6 both a BTC shock and alt recovery exist; shock is evaluated first and forces risk-off.
        self.assertEqual(float(state.iloc[5]), 0.0)


if __name__ == "__main__":
    unittest.main()
