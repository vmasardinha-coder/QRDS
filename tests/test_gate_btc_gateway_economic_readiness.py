import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.gate_btc_gateway_economic_readiness import audit


class GatewayEconomicReadinessTests(unittest.TestCase):
    def capture(self, directory, composition=None, profile=None, extra=None):
        files = {
            "outputs/v2a1_run_manifest.json": json.dumps({
                "technical_status": "PASS", "operational_status": "NOT_APPROVED",
                "data_as_of": "2026-10-27",
                "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION"}),
            "outputs/scanner_snapshot_status.json": json.dumps({
                "snapshot_status": "SNAPSHOT_USABLE_WITH_DATA_WARNINGS"}),
            "outputs/strategy_compositions.csv": composition or (
                "strategy,asset,weight\nH,CASH,0.34\nH,BTC,0.66\nH,BTC_SHORT,-0.1\n"),
            "outputs/strategy_execution_profiles.csv": profile or (
                "strategy,gross_long,estimated_total_drag_bps_per_day,recommended_rebalance\n"
                "H,1,2.39,weekly_or_risk_trigger\n"),
        }
        files.update(extra or {})
        path = Path(directory) / "capture.zip"
        with zipfile.ZipFile(path, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return path

    def test_cash_is_not_market_long_and_cost_is_not_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(self.capture(directory))
        row = result["strategies"][0]
        self.assertAlmostEqual(row["market_long_excluding_cash"], .66)
        self.assertAlmostEqual(row["market_net_excluding_cash"], .56)
        self.assertAlmostEqual(row["market_gross_excluding_cash"], .76)
        self.assertTrue(row["drag_is_assumption_not_observed_cost"])
        self.assertFalse(result["nav_or_return_inferred_from_snapshot_count"])
        self.assertEqual(result["scientific_credit"], 0)

    def test_nonfinite_or_duplicate_weights_are_rejected(self):
        for text in ["strategy,asset,weight\nH,BTC,NaN\n",
                     "strategy,asset,weight\nH,BTC,.5\nH,BTC,.5\n"]:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(ValueError):
                    audit(self.capture(directory, composition=text))

    def test_profile_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                audit(self.capture(directory, composition="strategy,asset,weight\nOTHER,BTC,1\n"))

    def test_ambiguous_source_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                audit(self.capture(directory, extra={"strategy_compositions.csv": "x"}))

    def test_short_weights_require_explicit_execution_and_margin_bindings(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(self.capture(directory))
        contract = result["strategies"][0]["execution_contract"]
        self.assertTrue(contract["contains_short_weights"])
        self.assertEqual({r["id"] for r in contract["requirements"]},
                         {"DYN01", "DYN02", "DYN03", "DYN04", "DYN05", "DYN06", "DYN07"})
        short = next(r for r in contract["instrument_bindings"] if r["asset_label"] == "BTC_SHORT")
        self.assertEqual(short["side"], "SHORT")
        self.assertIsNone(short["venue"])
        self.assertNotIn("CASH", {r["asset_label"] for r in contract["instrument_bindings"]})
        self.assertFalse(contract["nav_available"])

    def test_weekly_label_does_not_freeze_calendar_or_activate_old_snapshots(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(self.capture(directory,
                composition="strategy,asset,weight\nH,CASH,.4\nH,BTC,.6\n",
                profile="strategy,gross_long,estimated_total_drag_bps_per_day,recommended_rebalance\nH,1,1,weekly\n"))
        contract = result["strategies"][0]["execution_contract"]
        self.assertEqual(contract["recommended_rebalance"], "weekly")
        self.assertFalse(contract["recommendation_is_frozen_execution_policy"])
        self.assertFalse(contract["contains_short_weights"])
        self.assertTrue(all(r["status"] == "UNBOUND" for r in contract["requirements"]))
        self.assertIsNone(contract["activation_at_utc"])
        self.assertIsNone(contract["frozen_protocol_sha256"])
        self.assertEqual(result["execution_contract_summary"]["profiles_ready_for_economic_ledger"], 0)
        self.assertEqual(contract["economic_observations"], 0)

    def test_profile_specific_instrument_intake_preserves_weights(self):
        with tempfile.TemporaryDirectory() as directory:
            result = audit(self.capture(directory,
                composition="strategy,asset,weight\nA,BTC,.7\nA,CASH,.3\nB,ETH,-.4\nB,CASH,1\n",
                profile="strategy,gross_long,estimated_total_drag_bps_per_day,recommended_rebalance\nA,1,1,weekly\nB,1,2,weekly_or_risk_trigger\n"))
        first, second = result["strategies"]
        self.assertEqual(first["execution_contract"]["instrument_bindings"][0]["asset_label"], "BTC")
        self.assertEqual(second["execution_contract"]["instrument_bindings"][0]["weight"], -.4)
        self.assertFalse(first["execution_contract"]["contains_short_weights"])
        self.assertTrue(second["execution_contract"]["contains_short_weights"])
        self.assertEqual(result["execution_contract_summary"]["profile_count"], 2)


if __name__ == "__main__":
    unittest.main()

