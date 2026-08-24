from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "gate_btc_factory_delta_c1.py"
PREREG = ROOT / "research" / "factory_delta_c1_prereg.json"


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
        self.assertIn(result["status"], {"CLOSED_NULL", "SURVIVORS_READY_FOR_FREEZE"})
        self.assertEqual(result["comparison_capital_brl"], 180000)
        self.assertFalse(result["h1_economics_read"])
        self.assertFalse(result["partial_prospective_economics_read"])
        self.assertEqual(result["orders"], 0)
        self.assertEqual(result["real_capital"], 0)
        self.assertFalse(result["engine_feed"])
        self.assertEqual(set(result["families"]), set(p["families"]))


if __name__ == "__main__":
    unittest.main()
