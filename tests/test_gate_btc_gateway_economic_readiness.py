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


if __name__ == "__main__":
    unittest.main()
