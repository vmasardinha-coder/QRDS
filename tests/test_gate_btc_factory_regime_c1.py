from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gate_btc_factory_regime_c1.py"
PREREG = ROOT / "research" / "factory_regime_c1_prereg.json"


def load_module():
    spec = importlib.util.spec_from_file_location("factory_regime_c1", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RegimeC1Tests(unittest.TestCase):
    def test_prereg_safety_and_family_budget(self):
        p = json.loads(PREREG.read_text(encoding="utf-8"))
        self.assertTrue(p["generated_before_results"])
        self.assertEqual(len(p["families"]), 5)
        self.assertEqual(p["capital_comparison_brl"], 180000)
        self.assertTrue(p["source_contract"]["qos_incumbents_read_only"])
        self.assertTrue(p["source_contract"]["exploratory_bottom_probabilities_not_labels"])
        self.assertEqual(p["safety"]["ORDERS"], 0)
        self.assertEqual(p["safety"]["REAL_CAPITAL"], 0)
        self.assertFalse(p["safety"]["ENGINE_FEED"])
        self.assertTrue(p["safety"]["NO_BACKFILL"])

    def test_fixture_pipeline_runs_without_lookahead_contract_break(self):
        m = load_module()
        p = m.load_prereg()
        raw, macro_raw = m.fixture_inputs()
        prices = m.panelize(raw, p["historical_cutoff_exclusive"])
        macro = m.align_macro(macro_raw, prices.index)
        result = m.evaluate(prices, macro, p)
        self.assertIn(result["status"], {"CLOSED_NULL", "CLOSED_NULL_WITH_DATA_GAPS", "SURVIVORS_READY_FOR_FREEZE"})
        self.assertEqual(result["comparison_capital_brl"], 180000)
        self.assertFalse(result["h1_economics_read"])
        self.assertFalse(result["partial_prospective_economics_read"])
        self.assertEqual(result["orders"], 0)
        self.assertEqual(result["real_capital"], 0)
        self.assertFalse(result["engine_feed"])
        self.assertEqual(set(result["families"]), set(p["families"]))
        self.assertEqual(result["data_gaps"], [])


if __name__ == "__main__":
    unittest.main()
