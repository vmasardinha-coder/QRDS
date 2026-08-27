import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from tools.gate_btc_2_selector_alpha_terminal import (
    BOUNDARY,
    EXPECTED_CONTRACT_SHA256,
    STATUS_SCHEMA,
    TERMINAL_MANIFEST_SCHEMA,
    apply_period_factors,
    canonical_hash,
    file_sha256,
    fixed_rule,
    mix_return,
    random_rule,
    return_metrics,
    verify_outer_only_file_binding,
)


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "migration"


def read_json(name: str):
    return json.loads((MIGRATION / name).read_text(encoding="utf-8"))


class SelectorAlphaTerminalTests(unittest.TestCase):
    def test_shared_baseline_shock_is_applied_exactly_once(self):
        week = pd.Timestamp("2026-01-30")
        weekly = pd.DataFrame(
            {
                "UNFILTERED_PIT": [0.10],
                "SELECTED_MODERADA_PIT": [0.20],
                "SELECTED_ULTRA_PIT": [0.30],
                "btc_return": [0.05],
            },
            index=[week],
        )
        periods = [{
            "missing": 2,
            "missing_fraction": 0.20,
            "baseline_return": 0.10,
            "moderada_return": 0.20,
            "ultra_return": 0.30,
            "baseline_terminal_return": 0.10,
            "baseline_terminal_week": week,
            "moderada_terminal_return": 0.20,
            "moderada_terminal_week": week,
            "ultra_terminal_return": 0.30,
            "ultra_terminal_week": week,
        }]
        stressed = apply_period_factors(
            periods,
            weekly,
            lambda _period, _key: (-0.50, 0.0, 0.0, True),
        )
        self.assertAlmostEqual(
            stressed.at[week, "UNFILTERED_PIT"],
            mix_return(0.10, 0.20, -0.50),
        )
        self.assertAlmostEqual(stressed.at[week, "SELECTED_MODERADA_PIT"], 0.20)
        self.assertAlmostEqual(stressed.at[week, "SELECTED_ULTRA_PIT"], 0.30)

    def test_random_missingness_shares_one_baseline_draw_between_arms(self):
        period = {
            "signal_date": pd.Timestamp("2026-01-31"),
            "missing": 3,
            "covered": 7,
            "total": 10,
            "moderada_n": 4,
            "ultra_n": 6,
            "empirical_returns": np.asarray([-0.8, -0.2, 0.1, 0.7]),
        }
        rule = random_rule(np.random.default_rng(104729))
        moderada = rule(period, "moderada")
        ultra = rule(period, "ultra")
        self.assertEqual(moderada[0], ultra[0])
        self.assertTrue(moderada[3] and ultra[3])

    def test_concentrated_rule_uses_frozen_union_period(self):
        period = {
            "empirical_returns": np.asarray([-0.5, 0.9]),
            "moderada_positive_contribution": True,
            "ultra_positive_contribution": False,
        }
        rule = fixed_rule("concentrated")
        self.assertEqual(rule(period, "moderada"), rule(period, "ultra"))
        self.assertTrue(rule(period, "moderada")[3])

    def test_monotone_wealth_has_zero_drawdown(self):
        metrics = return_metrics(np.asarray([0.10, 0.20, 0.05]))
        self.assertEqual(metrics["MAX_DD"], 0.0)

    def test_terminal_outputs_are_self_consistent_and_hash_sealed(self):
        status = read_json("GATE_BTC_2_SELECTOR_ALPHA_STATUS.json")
        manifest = read_json("GATE_BTC_2_SELECTOR_ALPHA_TERMINAL_MANIFEST.json")
        self.assertEqual(status["schema"], STATUS_SCHEMA)
        unsigned_status = copy.deepcopy(status)
        claimed_status_hash = unsigned_status.pop("status_sha256")
        self.assertEqual(claimed_status_hash, canonical_hash(unsigned_status))
        self.assertEqual(manifest["schema"], TERMINAL_MANIFEST_SCHEMA)
        unsigned_manifest = copy.deepcopy(manifest)
        claimed_manifest_hash = unsigned_manifest.pop("manifest_sha256")
        self.assertEqual(claimed_manifest_hash, canonical_hash(unsigned_manifest))
        for name, expected in manifest["outputs"].items():
            self.assertEqual(file_sha256(MIGRATION / name), expected)
        self.assertEqual(manifest["boundary"], BOUNDARY)
        self.assertFalse(manifest["phase_4_authorized"])
        self.assertEqual(
            file_sha256(MIGRATION / "GATE_BTC_2_SELECTOR_ALPHA_PROGRAM_CONTRACT_V1.json"),
            EXPECTED_CONTRACT_SHA256,
        )

    def test_outer_only_control_file_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            evidence = directory / "evidence"
            evidence.mkdir()
            expected = {
                "COVERAGE_BY_SIGNAL.csv": b"signal_date,coverage\n2026-01-31,0.95\n",
                "SHA256SUMS.txt": b"a" * 64 + b"  sealed.csv\n",
            }
            for name, content in expected.items():
                (evidence / name).write_bytes(content)
            archive_path = directory / "evidence.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                for name, content in expected.items():
                    archive.writestr(name, content)
            verify_outer_only_file_binding(archive_path, evidence)
            (evidence / "COVERAGE_BY_SIGNAL.csv").write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "not bound to outer artifact"):
                verify_outer_only_file_binding(archive_path, evidence)

    def test_pit_reconstruction_is_partial_and_never_backfilled(self):
        pit = read_json("GATE_BTC_2_SELECTOR_ALPHA_PIT_RECONSTRUCTION_SEAL.json")
        self.assertEqual(pit["PIT_UNIVERSE_TOTAL_EXPECTED"], 10254)
        self.assertEqual(pit["PIT_UNIVERSE_PHYSICAL_RECOVERED"], 9819)
        self.assertEqual(pit["UNRESOLVED_ASSET_MEMBERSHIPS"], 435)
        self.assertEqual(pit["SNAPSHOTS_AT_OR_ABOVE_95"], 63)
        self.assertEqual(pit["SNAPSHOTS_BELOW_95"], 11)
        self.assertAlmostEqual(pit["PIT_COVERAGE_PCT"], 95.75775307197192)
        self.assertFalse(pit["g2_pit_universe_pass"])
        self.assertFalse(pit["synthetic_official_fill"])
        self.assertFalse(pit["current_composition_applied_to_past"])

    def test_four_leads_are_only_existing_bounded_source_instances(self):
        ledger = read_json("GATE_BTC_2_SELECTOR_ALPHA_SOURCE_ADMISSION_LEDGER.json")
        self.assertEqual(ledger["existing_bounded_pit_source_instances_admitted"], 4)
        self.assertEqual(ledger["new_sources_discovered"], 0)
        self.assertEqual(ledger["new_v2a_sources_admitted"], 0)
        self.assertEqual(ledger["new_v2a_assets_recovered"], 0)
        self.assertEqual({row["current_gap_symbol"] for row in ledger["decisions"]}, {"FF", "JASMY", "NEXO", "SYRUP"})
        for row in ledger["decisions"]:
            self.assertTrue(row["existing_pit_source_instance_admitted"])
            self.assertFalse(row["new_v2a_source_admitted"])
            self.assertFalse(row["current_v2a_mutated"])
            self.assertEqual(len(row["selected_history_file_sha256"]), 64)
            self.assertEqual(row["gate_states"]["CAUSALITY"], "PASS_BOUNDED_NO_FUTURE_STITCH")
        nexo = next(row for row in ledger["decisions"] if row["current_gap_symbol"] == "NEXO")
        self.assertTrue(nexo["pit_membership_before_selected_source_unresolved"])

    def test_observed_and_synthetic_sensitivity_close_the_hypothesis(self):
        report = read_json("GATE_BTC_2_SELECTOR_ALPHA_SURVIVORSHIP_SENSITIVITY_REPORT.json")
        moderada = report["observed"]["SELECTED_MODERADA_PIT"]["direct_alpha_vs_unfiltered"]
        ultra = report["observed"]["SELECTED_ULTRA_PIT"]["direct_alpha_vs_unfiltered"]
        self.assertAlmostEqual(moderada["alpha_weekly"], -0.0025296416657321127, places=15)
        self.assertAlmostEqual(ultra["alpha_weekly"], -0.0015944374424663856, places=15)
        self.assertLess(moderada["alpha_weekly"], 0.0)
        self.assertLess(ultra["alpha_weekly"], 0.0)
        adversarial = report["fixed_scenarios"]["ADVERSARIAL_MISSINGNESS"]
        for arm in ("SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"):
            self.assertLessEqual(adversarial[arm]["direct_alpha_vs_unfiltered"]["alpha_weekly"], 0.0)
        random = report["random_missingness"]
        self.assertEqual(random["total_draws"], 1000)
        self.assertEqual(random["seeds"], [104729, 130363, 155921, 196613, 262147])
        self.assertLess(random["direct_alpha_vs_unfiltered"]["SELECTED_MODERADA_PIT"]["probability_positive"], 0.01)
        self.assertLess(random["direct_alpha_vs_unfiltered"]["SELECTED_ULTRA_PIT"]["probability_positive"], 0.02)
        self.assertEqual(len(report["loss_grid"]), 101)
        self.assertTrue(report["stop_gate"]["triggered"])
        self.assertFalse(report["stop_gate"]["phase_4_authorized"])
        self.assertFalse(report["synthetic_values_entered_official_dataset"])

    def test_executive_status_stops_later_phases_without_retune(self):
        status = read_json("GATE_BTC_2_SELECTOR_ALPHA_STATUS.json")
        self.assertEqual(status["CURRENT_GATE"], "FAIL_CLOSED_SELECTOR_ALPHA_REFUTED_NO_RETUNE")
        self.assertEqual(status["SELECTOR_ALPHA_STATUS"], "SELECTOR_ALPHA_REFUTED_CURRENT_FROZEN_SELECTOR")
        self.assertEqual(status["current_v2a_reference"]["attempted"], 150)
        self.assertEqual(status["current_v2a_reference"]["loaded"], 95)
        self.assertFalse(status["current_v2a_reference"]["mutated_by_program"])
        self.assertEqual(len(status["financial_metrics"]), 24)
        for phase in (
            "PHASE_4_SELECTOR_ABLATION",
            "PHASE_5_TIME_REGIME_ROBUSTNESS",
            "PHASE_6_INDEPENDENT_REPLICATION",
            "PHASE_7_PROSPECTIVE_SELECTOR_TRACK",
        ):
            self.assertIn("STOP", status["phase_status"][phase])
        self.assertFalse(status["terminal_decision"]["retune"])
        self.assertFalse(status["terminal_decision"]["new_selector"])
        self.assertEqual(status["promotion_ladders"]["OPERATIONAL_PROMOTION"], "NOT_APPROVED")
        self.assertEqual(status["boundary"], BOUNDARY)

    def test_runner_and_workflow_have_no_market_collection_or_schedule(self):
        source = (ROOT / "tools" / "gate_btc_2_selector_alpha_terminal.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "gate-btc-2-selector-alpha-terminal.yml").read_text(encoding="utf-8")
        self.assertNotIn("\nimport requests\n", source)
        self.assertNotIn("\nfrom requests", source)
        self.assertNotIn("\nimport urllib", source)
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  schedule:", workflow)
        self.assertIn('PIT_ARTIFACT_ID: "9027220602"', workflow)
        self.assertIn("actions/artifacts/${PIT_ARTIFACT_ID}/zip", workflow)
        self.assertNotIn("binance.com/api", workflow.lower())
        self.assertNotIn("coinmarketcap.com/historical", workflow.lower())


if __name__ == "__main__":
    unittest.main()
