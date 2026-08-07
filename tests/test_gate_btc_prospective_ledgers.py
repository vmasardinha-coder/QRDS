import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

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

    def test_d50_conflict_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / "frozen.json"
            candidate = root / "candidate.json"
            output = root / "report.json"
            frozen.write_text('{"date":"2026-08-01","value":1}', encoding="utf-8")
            candidate.write_text('{"date":"2026-08-01","value":2}', encoding="utf-8")
            rc = audit_d50(Namespace(frozen_row=frozen, candidate_row=candidate, ignore_field=None, output=output))
            self.assertEqual(rc, 2)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "FAIL_IMMUTABLE_ROW_CHANGED")
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(json.loads(frozen.read_text(encoding="utf-8"))["value"], 1)

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


if __name__ == "__main__":
    unittest.main()
