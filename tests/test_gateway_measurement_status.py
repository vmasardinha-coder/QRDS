import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.gate_btc_measurement_common import load_json, safe_gateway


class GatewayMeasurementStatusTests(unittest.TestCase):
    def _inputs(self, root: Path, data_as_of: str):
        manifest = root / "manifest.json"
        status = root / "status.json"
        compositions = root / "compositions.csv"
        profiles = root / "profiles.csv"
        manifest.write_text(json.dumps({
            "run_utc": f"{data_as_of}T23:59:00Z",
            "data_as_of": data_as_of,
            "technical_status": "PASS",
            "data_quality_status": "PASS",
            "operational_status": "NOT_APPROVED",
            "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
            "errors": [],
        }), encoding="utf-8")
        status.write_text(json.dumps({
            "snapshot_status": "SNAPSHOT_USABLE_RESEARCH_ONLY",
            "warning_failed_checks": [],
        }), encoding="utf-8")
        compositions.write_text("strategy,asset,weight\nA,BTC,1\n", encoding="utf-8")
        profiles.write_text("strategy,mode\nA,shadow\n", encoding="utf-8")
        return manifest, status, compositions, profiles

    def test_new_close_and_duplicate_keep_v2_status_without_double_counting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger"
            manifest, status, compositions, profiles = self._inputs(root, "2026-08-07")
            args = Namespace(
                manifest=manifest,
                snapshot_status=status,
                compositions=compositions,
                execution_profiles=profiles,
                snapshot_id="2026-08-07",
                ledger_dir=ledger,
            )
            self.assertEqual(safe_gateway(args), 0)
            first = load_json(ledger / "STATUS.json")
            self.assertEqual(first["schema"], "gate_btc.gateway_dynamics_ledger_status.v2")
            self.assertEqual(first["valid_snapshot_count"], 1)
            self.assertEqual(first["latest_source_data_as_of"], "2026-08-07")
            self.assertEqual(first["next_expected_source_data_as_of"], "2026-08-08")

            self.assertEqual(safe_gateway(args), 0)
            duplicate = load_json(ledger / "STATUS.json")
            self.assertEqual(duplicate["schema"], "gate_btc.gateway_dynamics_ledger_status.v2")
            self.assertEqual(duplicate["valid_snapshot_count"], 1)
            self.assertEqual(duplicate["same_source_close_diagnostic_count"], 1)
            self.assertFalse(duplicate["same_source_close_counter_incremented"])
            self.assertEqual(len(list((ledger / "snapshots").glob("*.json"))), 1)
            self.assertEqual(len(list((ledger / "diagnostics").glob("*.json"))), 1)


if __name__ == "__main__":
    unittest.main()
