import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_survivorship_alpha_audit import BASKETS, run


class SurvivorshipAlphaAuditTests(unittest.TestCase):
    def provenance(self, remaining=False):
        return {
            "schema": "gate_btc.survivorship_alpha_input_provenance.v1",
            "point_in_time_universe": True,
            "point_in_time_selection_recomputed": True,
            "current_survivor_only": False,
            "confirmed_terminal_loss_policy_validated": True,
            "provisional_terminal_returns_synthesized": False,
            "provisional_or_unresolved_censoring_remaining": remaining,
            "engine_feed": False,
            "methodology_changes": 0,
            "orders_generated": 0,
            "real_capital_used": 0,
        }

    def rows(self, coverage=1.0):
        values = [-0.08, -0.03, 0.01, 0.04, 0.07, -0.05, 0.02, 0.09, -0.01, 0.03, 0.06, -0.04]
        alpha = {
            "UNFILTERED_PIT": 0.002,
            "SELECTED_MODERADA_PIT": 0.010,
            "SELECTED_ULTRA_PIT": 0.007,
        }
        beta = {
            "UNFILTERED_PIT": 1.0,
            "SELECTED_MODERADA_PIT": 1.1,
            "SELECTED_ULTRA_PIT": 1.03,
        }
        rows = []
        covered = int(round(100 * coverage))
        for index, btc in enumerate(values):
            week = f"2026-{1 + index // 4:02d}-{7 + (index % 4) * 7:02d}"
            # Keep valid ISO dates while still spanning fixed calendar windows.
            from datetime import date, timedelta
            week = (date(2026, 1, 4) + timedelta(days=7 * index)).isoformat()
            regime = "BULL" if btc > 0.025 else ("BEAR" if btc < -0.025 else "NEUTRAL")
            noise = (index % 3 - 1) * 0.0005
            for basket in BASKETS:
                rows.append({
                    "week_end": week,
                    "basket": basket,
                    "basket_return": alpha[basket] + beta[basket] * btc + noise,
                    "btc_return": btc,
                    "regime": regime,
                    "covered_eligible_assets": covered,
                    "total_eligible_assets": 100,
                    "coverage_ratio": coverage,
                })
        return rows

    def test_full_pit_audit_recovers_positive_selection_delta_alpha(self):
        payload = run(self.rows(), self.provenance(remaining=False), hac_lag=4)
        self.assertEqual(payload["status"], "PASS_FULL_COVERAGE_AUDIT")
        self.assertAlmostEqual(payload["results"]["UNFILTERED_PIT"]["alpha_weekly"], 0.002, delta=0.001)
        self.assertGreater(payload["results"]["SELECTED_MODERADA_PIT"]["delta_alpha_vs_unfiltered_weekly"], 0)
        self.assertGreater(payload["results"]["SELECTED_ULTRA_PIT"]["delta_alpha_vs_unfiltered_weekly"], 0)
        self.assertFalse(payload["engine_feed"])
        self.assertEqual(payload["methodology_changes"], 0)
        self.assertEqual(payload["orders_generated"], 0)
        self.assertEqual(payload["real_capital_used"], 0)
        self.assertIn("by_regime", payload["decomposition"])

    def test_partial_coverage_remains_research_only(self):
        payload = run(self.rows(coverage=0.80), self.provenance(remaining=True), hac_lag=4)
        self.assertEqual(payload["status"], "PARTIAL_COVERAGE_RESEARCH_ONLY")
        self.assertAlmostEqual(payload["coverage"]["min_ratio"], 0.8)

    def test_survivor_only_provenance_fails_closed(self):
        provenance = self.provenance()
        provenance["current_survivor_only"] = True
        with self.assertRaisesRegex(RuntimeError, "current-survivor-only"):
            run(self.rows(), provenance)

    def test_selection_must_be_recomputed_point_in_time(self):
        provenance = self.provenance()
        provenance["point_in_time_selection_recomputed"] = False
        with self.assertRaisesRegex(RuntimeError, "not recomputed point-in-time"):
            run(self.rows(), provenance)

    def test_calendar_mismatch_fails_closed(self):
        rows = self.rows()
        rows = [row for row in rows if not (row["basket"] == "SELECTED_ULTRA_PIT" and row["week_end"] == rows[0]["week_end"])]
        with self.assertRaisesRegex(RuntimeError, "same weekly calendar"):
            run(rows, self.provenance())

    def test_synthetic_provisional_terminal_return_is_prohibited(self):
        provenance = self.provenance()
        provenance["provisional_terminal_returns_synthesized"] = True
        with self.assertRaisesRegex(RuntimeError, "synthetic provisional"):
            run(self.rows(), provenance)


if __name__ == "__main__":
    unittest.main()
