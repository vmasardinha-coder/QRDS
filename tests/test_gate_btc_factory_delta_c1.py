from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest
import copy
import numpy as np
import pandas as pd
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gate_btc_factory_delta_c1.py"
PREREG = ROOT / "tools" / "gate_btc_factory_delta_c1_prereg.json"


def load_module():
    spec = importlib.util.spec_from_file_location("factory_delta_c1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DeltaC1Tests(unittest.TestCase):
    def test_prereg_safety_and_family_budget(self):
        p = json.loads(PREREG.read_text(encoding="utf-8"))
        self.assertTrue(p["generated_before_results"])
        self.assertEqual(len(p["families"]), 5)
        self.assertEqual(p["capital_comparison_brl"], 180000)
        self.assertEqual(p["historical_cutoff_exclusive"], "2026-08-10")
        self.assertTrue(p["source_contract"]["incumbents_read_only"])
        self.assertTrue(p["source_contract"]["external_delta_not_tuning_target"])
        self.assertEqual(p["safety"]["ORDERS"], 0)
        self.assertEqual(p["safety"]["REAL_CAPITAL"], 0)
        self.assertFalse(p["safety"]["ENGINE_FEED"])
        self.assertTrue(p["safety"]["NO_BACKFILL"])

    def test_fixture_pipeline_is_deterministic_and_safe(self):
        m = load_module()
        p = m.load_prereg()
        raw1 = m.fixture_ohlc()
        raw2 = m.fixture_ohlc()
        self.assertEqual(raw1.to_csv(index=False), raw2.to_csv(index=False))
        prices = m.panelize(raw1, p["historical_cutoff_exclusive"])
        result = m.evaluate(prices, p)
        self.assertIn(result["status"], {"CLOSED_NULL", "CAUSAL_CANDIDATES_REQUIRE_SOURCE_QUALIFICATION"})
        self.assertFalse(result["freeze_eligible"])
        self.assertFalse(result["legacy_v1_admission_allowed"])
        self.assertEqual(result["comparison_capital_brl"], 180000)
        self.assertFalse(result["h1_economics_read"])
        self.assertFalse(result["partial_prospective_economics_read"])
        self.assertEqual(result["orders"], 0)
        self.assertEqual(result["real_capital"], 0)
        self.assertFalse(result["engine_feed"])
        self.assertEqual(set(result["families"]), set(p["families"]))

    def causal_case(self):
        m = load_module()
        p = copy.deepcopy(m.load_prereg())
        p['execution'].update(top_n=1, bottom_n=1, fee_bps_per_turnover_unit=0)
        prices = pd.DataFrame({'BTC': [100]*5, 'A': [100, 100, 200, 220, 220],
                               'B': [100, 100, 50, 45, 45]},
                              index=pd.date_range('2026-01-01', periods=5))
        cfg = {'lookback': 1, 'rebalance_days': 2, 'gross_long': .7, 'gross_short': .3}
        return m, p, prices, cfg

    def test_new_signal_cannot_earn_its_own_bar(self):
        m, p, prices, cfg = self.causal_case()
        r = m.run_variant(prices, 'DELTA_C1_PERSISTENCE', cfg, p)
        self.assertEqual(r.iloc[2], 0.0)
        self.assertAlmostEqual(r.iloc[3], .1)

    def test_rebalance_fee_charged_once_at_decision_close(self):
        m, p, prices, cfg = self.causal_case()
        p['execution']['fee_bps_per_turnover_unit'] = 8
        r = m.run_variant(prices, 'DELTA_C1_PERSISTENCE', cfg, p)
        self.assertAlmostEqual(r.iloc[2], -.0008)
        self.assertAlmostEqual(r.iloc[3], .1)

    def test_held_missing_quote_is_not_zero_return(self):
        m, p, prices, cfg = self.causal_case()
        prices.loc[prices.index[3], 'A'] = np.nan
        r = m.run_variant(prices, 'DELTA_C1_PERSISTENCE', cfg, p)
        self.assertTrue(pd.isna(r.iloc[3]))

    def test_all_families_ignore_future_prices(self):
        m, p, prices, cfg = self.causal_case()
        # A later shock cannot change returns before that shock.
        altered = prices.copy()
        altered.iloc[4] *= 5
        for family, spec in p['families'].items():
            a = m.run_variant(prices, family, spec['central'], p)
            b = m.run_variant(altered, family, spec['central'], p)
            pd.testing.assert_series_equal(a.iloc[:4], b.iloc[:4])

    def test_missing_held_returns_block_admission_even_with_good_metrics(self):
        m = load_module()
        metrics = {'n': 100, 'total_return': .2, 'sharpe': 2,
                   'max_drawdown': -.01, 'invalid_held_return_count': 1}
        self.assertFalse(m.passes(metrics, m.load_prereg()['gates']))

    def test_terminal_closure_has_no_candidates_awaiting_freeze(self):
        m = load_module()
        result = m.closure_result()
        self.assertEqual(result['status'], 'CLOSED_NO_CANONICAL_SURVIVOR_EVIDENCE')
        self.assertEqual(result['survivors'], [])
        self.assertFalse(result['freeze_pending'])
        self.assertFalse(result['admission_allowed'])

    def test_public_invocation_cannot_collect_or_recreate_candidates(self):
        m = load_module()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / 'RESULT.json'
            with patch('sys.argv', ['delta', '--mode', 'public', '--out', str(out)]), \
                    patch.object(m, 'public_ohlc', side_effect=AssertionError('no public rerun')), \
                    patch.object(m, 'evaluate', side_effect=AssertionError('no economic rerun')):
                self.assertEqual(m.main(), 0)
            result = json.loads(out.read_text())
            self.assertFalse(result['public_collection_attempted'])
            self.assertEqual(result['scientific_credit'], 0)


if __name__ == "__main__":
    unittest.main()
