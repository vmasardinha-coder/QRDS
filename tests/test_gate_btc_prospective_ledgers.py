import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from tools.gate_btc_measurement_common import validate_contract
from tools.gate_btc_prospective_ledgers import append_gateway, audit_d50


class ProspectiveLedgerTests(unittest.TestCase):
    def test_gateway_genesis_and_immutability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "manifest.json"
            status = root / "status.json"
            comps = root / "compositions.csv"
            profiles = root / "profiles.csv"
            manifest.write_text(json.dumps({
                "run_utc": "2026-08-06T00:00:00Z",
                "data_as_of": "2026-08-05",
                "technical_status": "PASS",
                "data_quality_status": "PASS",
                "operational_status": "NOT_APPROVED",
                "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
                "errors": [],
            }), encoding="utf-8")
            status.write_text(json.dumps({"snapshot_status": "SNAPSHOT_USABLE_RESEARCH_ONLY", "warning_failed_checks": []}), encoding="utf-8")
            comps.write_text("strategy,asset,weight\nA,BTC,1\n", encoding="utf-8")
            profiles.write_text("strategy,mode\nA,manual\n", encoding="utf-8")
            args = Namespace(manifest=manifest, snapshot_status=status, compositions=comps, execution_profiles=profiles,
                             snapshot_id="2026-08-05", ledger_dir=root / "ledger")
            self.assertEqual(append_gateway(args), 0)
            record = json.loads((root / "ledger/snapshots/2026-08-05.json").read_text(encoding="utf-8"))
            self.assertEqual(record["sequence"], 1)
            self.assertTrue(record["genesis"])
            with self.assertRaises(RuntimeError):
                append_gateway(args)

    def test_d50_economic_conflict_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / "frozen.json"
            candidate = root / "candidate.json"
            output = root / "report.json"
            frozen.write_text('{"date":"2026-08-01","strategy":"D50_CONTROL","value":1}', encoding="utf-8")
            candidate.write_text('{"date":"2026-08-01","strategy":"D50_CONTROL","value":2}', encoding="utf-8")
            rc = audit_d50(Namespace(frozen_row=frozen, candidate_row=candidate, ignore_field=None, output=output))
            self.assertEqual(rc, 2)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "FAIL_IMMUTABLE_ECONOMIC_ROW_CHANGED")
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(json.loads(frozen.read_text(encoding="utf-8"))["value"], 1)

    def test_d50_provenance_only_revision_uses_canonical_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / "frozen.json"
            candidate = root / "candidate.json"
            output = root / "report.json"
            frozen_payload = {
                "date": "2026-08-01",
                "strategy": "D50_CONTROL",
                "net_return": -0.0010251858188263,
                "source_bar_sha256": "old-source",
                "replay_row_sha256": "old-replay",
            }
            candidate_payload = {
                **frozen_payload,
                "source_bar_sha256": "new-source",
                "replay_row_sha256": "new-replay",
            }
            frozen.write_text(json.dumps(frozen_payload), encoding="utf-8")
            candidate.write_text(json.dumps(candidate_payload), encoding="utf-8")
            rc = audit_d50(Namespace(frozen_row=frozen, candidate_row=candidate, ignore_field=None, output=output))
            self.assertEqual(rc, 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS_PROVENANCE_ONLY_SOURCE_REVISION")
            self.assertTrue(report["economic_fields_identical"])
            self.assertTrue(report["source_revision_only"])
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(json.loads(frozen.read_text(encoding="utf-8")), frozen_payload)

    def test_frozen_lock_contract_excludes_lock75(self):
        repo = Path(__file__).resolve().parents[1]
        lock_contract = json.loads(
            (repo / "config/lock25_50_shadow_contract_v1.json").read_text(encoding="utf-8")
        )
        replay_contract = json.loads(
            (repo / "migration/reporting/bull_replay_contract.json").read_text(encoding="utf-8")
        )

        self.assertEqual(set(lock_contract["variants"]), {"LOCK25", "LOCK50"})
        self.assertNotIn("LOCK75", lock_contract["variants"])
        self.assertEqual(replay_contract["locks"], ["CONTROL", "LOCK25", "LOCK50"])
        self.assertNotIn("LOCK75", replay_contract["locks"])
        validate_contract(lock_contract)

        bad = json.loads(json.dumps(lock_contract))
        bad["variants"]["LOCK75"] = {
            "arming_level_multiple": 1.75,
            "protected_share_of_accumulated_profit": 0.75,
            "destination": "VIRTUAL_CASH",
            "retracement_trigger_pct": 0.20,
            "double_counting_prohibited": True,
        }
        with self.assertRaisesRegex(RuntimeError, "exactly LOCK25 and LOCK50"):
            validate_contract(bad)


if __name__ == "__main__":
    unittest.main()
