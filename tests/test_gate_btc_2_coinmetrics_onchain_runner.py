from __future__ import annotations

import importlib.util
import json
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "gate_btc_2_coinmetrics_onchain_runner.py"
spec = importlib.util.spec_from_file_location("coinmetrics_runner", MODULE_PATH)
cm = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(cm)


def _rows(n: int = 20, *, falling_after: int | None = None):
    start = date(2026, 1, 1)
    rows = []
    for i in range(n):
        adr = 100.0 + i
        if falling_after is not None and i >= falling_after:
            adr = 500.0 - i * 10.0
        rows.append({"day": start + timedelta(days=i), "adr": adr, "price": 100.0 + i})
    return rows


class CoinMetricsOnchainRunnerTests(unittest.TestCase):
    def test_parse_rows_rejects_unexpected_pagination(self):
        raw = json.dumps({"data": [], "next_page_token": "more"}).encode()
        with self.assertRaisesRegex(ValueError, "pagination"):
            cm.parse_rows(raw)

    def test_build_observations_enforces_full_day_embargo_and_7d_feature(self):
        rows = _rows(12)
        obs, details = cm.build_observations(rows)
        self.assertEqual(details["duplicate_timestamps"], 0)
        self.assertTrue(details["strictly_increasing"])
        self.assertTrue(obs)
        first = obs[0]
        self.assertEqual(first["feature_day"], "2026-01-08")
        self.assertEqual(first["target_start_day"], "2026-01-09")
        self.assertEqual(first["target_end_day"], "2026-01-10")
        self.assertEqual(first["adr_now"], 107.0)
        self.assertEqual(first["adr_7d_ago"], 100.0)
        self.assertEqual(first["state_long"], 1)
        self.assertAlmostEqual(first["gross_return"], 109.0 / 108.0, places=12)

    def test_duplicate_dates_are_reported_not_silently_credited(self):
        rows = _rows(12)
        rows.append(dict(rows[5]))
        _, details = cm.build_observations(rows)
        self.assertEqual(details["duplicate_timestamps"], 1)

    def test_replay_charges_cost_only_on_state_transitions_and_final_exit(self):
        obs = [
            {"state_long": 0, "gross_return": 1.10},
            {"state_long": 1, "gross_return": 1.10},
            {"state_long": 1, "gross_return": 1.10},
            {"state_long": 0, "gross_return": 1.10},
        ]
        result = cm.replay(obs, initial=10000.0, cost=0.001)
        self.assertEqual(result["state_transitions_including_final_exit"], 2)
        expected = 10000.0 * 0.999 * 1.10 * 1.10 * 0.999
        self.assertAlmostEqual(result["strategy_final_equity"], expected, places=9)

    def test_replay_charges_final_exit_if_still_long(self):
        obs = [
            {"state_long": 1, "gross_return": 1.05},
            {"state_long": 1, "gross_return": 1.02},
        ]
        result = cm.replay(obs, initial=10000.0, cost=0.001)
        self.assertEqual(result["state_transitions_including_final_exit"], 2)
        expected = 10000.0 * 0.999 * 1.05 * 1.02 * 0.999
        self.assertAlmostEqual(result["strategy_final_equity"], expected, places=9)

    def test_baseline_uses_same_target_returns_with_entry_and_exit_costs(self):
        obs = [
            {"state_long": 0, "gross_return": 1.10},
            {"state_long": 0, "gross_return": 0.90},
        ]
        result = cm.replay(obs, initial=10000.0, cost=0.001)
        expected = 10000.0 * 0.999 * 1.10 * 0.90 * 0.999
        self.assertAlmostEqual(result["baseline_final_equity"], expected, places=9)

    def test_frozen_pass_rule_requires_both_drawdown_and_equity_conditions(self):
        obs = [
            {"state_long": 1, "gross_return": 1.10},
            {"state_long": 0, "gross_return": 0.50},
            {"state_long": 1, "gross_return": 2.00},
        ]
        result = cm.replay(obs, initial=10000.0, cost=0.0)
        self.assertGreaterEqual(result["drawdown_improvement_pp"], 5.0)
        self.assertGreaterEqual(result["strategy_to_baseline_final_equity_ratio"], 0.90)
        self.assertTrue(result["feature_pass"])

    def test_source_constants_and_safety_are_frozen(self):
        self.assertEqual(cm.START, "2020-01-01")
        self.assertEqual(cm.END, "2026-09-20")
        self.assertEqual(cm.COST, 0.001)
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('"historical_response_is_revision_versioned_pit_proven": False', text)
        self.assertIn('"factory_migration_authorized": False', text)
        self.assertIn('"economic_claim_authorized": False', text)
        self.assertIn('"no_retune": True', text)
        self.assertIn('"no_backfill": True', text)


if __name__ == "__main__":
    unittest.main()
