import hashlib
import json
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_d50_checkpoint_pack import CheckpointPackError, build_checkpoint_pack
from tools.gate_btc_d50_mirror_reconcile import ReconciliationError
from tests.test_gate_btc_d50_mirror_reconcile import (
    DATES,
    local_status,
    remote_status,
    rows_for_dates,
    write_csv,
)


class D50CheckpointPackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = self.root / "GATE_BTC_D50_AUTOPILOT_V2"
        self.state = self.base / "state"
        self.evidence = self.base / "evidence"
        self.output = self.evidence / "CHECKPOINT_PACKS"
        self.state.mkdir(parents=True)
        self.evidence.mkdir(parents=True)

        self.local_status_path = self.state / "D50_PROSPECTIVE_STATUS_V2.json"
        self.local_ledger_path = self.state / "d50_prospective_observations_v2.csv"
        self.remote_status_path = self.root / "REMOTE_STATUS.json"

        self.local_status_path.write_text(json.dumps(local_status()), encoding="utf-8")
        write_csv(self.local_ledger_path, rows_for_dates(DATES))
        self.remote_status_path.write_text(json.dumps(remote_status()), encoding="utf-8")

        self.repair = self.evidence / "D50_SOURCE_HASH_REPAIR_20260809_120000"
        backup = self.repair / "BACKUP"
        diagnostics = self.repair / "SOURCE_REVISION_DIAGNOSTICS"
        backup.mkdir(parents=True)
        diagnostics.mkdir(parents=True)
        write_csv(backup / "d50_prospective_observations_v2.csv", rows_for_dates(DATES[:4]))
        (self.repair / "RESULTADO_FINAL.txt").write_text(
            "\n".join(
                [
                    "STATUS=PASS_REPAIR_APPLIED_AND_DAILY_EXECUTED",
                    "FROZEN_ROWS_PRESERVED=True",
                    "RESEARCH_ONLY=True",
                    "OPERATIONAL_STATUS=NOT_APPROVED",
                    "ORDERS=0",
                    "CAPITAL=0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        diagnostic = {
            "schema": "gate_btc.d50_source_revision_diagnostic.v1",
            "status": "PASS_PROVENANCE_ONLY_FROZEN_ROW_PRESERVED",
            "date": "2026-08-01",
            "strategy": "D50_CONTROL",
            "economic_fields_identical": True,
            "source_revision_detected": True,
            "frozen_row_preserved": True,
            "mutation_performed": False,
            "counter_incremented_for_existing_date": False,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
            "orders": 0,
            "capital": 0,
        }
        (diagnostics / "2026-08-01_D50_CONTROL.json").write_text(
            json.dumps(diagnostic), encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def build(self):
        return build_checkpoint_pack(
            base=self.base,
            repo=None,
            output_dir=self.output,
            remote_status_path=self.remote_status_path,
            timestamp=datetime(2026, 8, 9, 20, 40, 0, tzinfo=timezone.utc),
        )

    def input_hashes(self):
        files = [
            self.local_status_path,
            self.local_ledger_path,
            self.remote_status_path,
            self.repair / "BACKUP" / "d50_prospective_observations_v2.csv",
            self.repair / "RESULTADO_FINAL.txt",
            self.repair / "SOURCE_REVISION_DIAGNOSTICS" / "2026-08-01_D50_CONTROL.json",
        ]
        return {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}

    def test_builds_immutable_candidate_pack_without_mutating_inputs(self):
        before = self.input_hashes()
        pack = self.build()
        after = self.input_hashes()
        self.assertEqual(before, after)
        self.assertTrue(pack.is_file())
        self.assertEqual(pack.name, "GATE_BTC_D50_CHECKPOINT_PACK_20260809_204000Z.zip")

        with zipfile.ZipFile(pack) as archive:
            names = set(archive.namelist())
            prefix = "GATE_BTC_D50_CHECKPOINT_PACK/"
            required = {
                prefix + "MANIFEST.json",
                prefix + "README.txt",
                prefix + "current/D50_PROSPECTIVE_STATUS_V2.json",
                prefix + "current/d50_prospective_observations_v2.csv",
                prefix + "repair/prior_d50_prospective_observations_v2.csv",
                prefix + "repair/RESULTADO_REPARO.txt",
                prefix + "repair/SOURCE_REVISION_DIAGNOSTICS/2026-08-01_D50_CONTROL.json",
                prefix + "remote/STATUS.json",
                prefix + "audit/D50_MIRROR_RECONCILIATION_AUDIT.json",
            }
            self.assertTrue(required.issubset(names))

            manifest = json.loads(archive.read(prefix + "MANIFEST.json"))
            audit = json.loads(
                archive.read(prefix + "audit/D50_MIRROR_RECONCILIATION_AUDIT.json")
            )
            self.assertEqual(manifest["schema"], "gate_btc.d50_checkpoint_pack.v1")
            self.assertEqual(manifest["audit_status"], "PASS_MIRROR_ADVANCE_CANDIDATE")
            self.assertTrue(manifest["candidate_only"])
            self.assertFalse(manifest["runtime_mutation_performed"])
            self.assertEqual(manifest["orders_generated"], 0)
            self.assertEqual(manifest["real_capital_used"], 0)
            self.assertEqual(audit["remote_mirror"]["current"], 4)
            self.assertEqual(audit["local_checkpoint"]["paired_observations"], 7)
            self.assertEqual(audit["local_checkpoint"]["latest_date"], "2026-08-08")

            listed = {item["path"]: item for item in manifest["files"]}
            self.assertIn("current/d50_prospective_observations_v2.csv", listed)
            packed_ledger = archive.read(prefix + "current/d50_prospective_observations_v2.csv")
            self.assertEqual(
                hashlib.sha256(packed_ledger).hexdigest(),
                listed["current/d50_prospective_observations_v2.csv"]["sha256"],
            )

    def test_fails_closed_when_successful_repair_evidence_is_missing(self):
        (self.repair / "RESULTADO_FINAL.txt").unlink()
        with self.assertRaisesRegex(CheckpointPackError, "no complete successful D50 repair evidence"):
            self.build()

    def test_fails_closed_when_repair_result_loses_zero_order_invariant(self):
        result = self.repair / "RESULTADO_FINAL.txt"
        result.write_text(
            "\n".join(
                [
                    "STATUS=PASS_REPAIR_APPLIED_AND_DAILY_EXECUTED",
                    "FROZEN_ROWS_PRESERVED=True",
                    "RESEARCH_ONLY=True",
                    "OPERATIONAL_STATUS=NOT_APPROVED",
                    "ORDERS=1",
                    "CAPITAL=0",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(CheckpointPackError, "no complete successful D50 repair evidence"):
            self.build()

    def test_fails_closed_when_frozen_prefix_changed(self):
        rows = rows_for_dates(DATES)
        rows[0] = dict(rows[0])
        rows[0]["net_return"] = "0.999"
        write_csv(self.local_ledger_path, rows)
        with self.assertRaisesRegex(ReconciliationError, "frozen prior row changed"):
            self.build()

    def test_fails_closed_when_historical_backfill_is_counted(self):
        status = local_status()
        status["historical_backfill_counted_as_prospective"] = True
        self.local_status_path.write_text(json.dumps(status), encoding="utf-8")
        with self.assertRaisesRegex(ReconciliationError, "historical backfill"):
            self.build()

    def test_pack_is_candidate_only_not_a_runtime_publisher(self):
        pack = self.build()
        with zipfile.ZipFile(pack) as archive:
            prefix = "GATE_BTC_D50_CHECKPOINT_PACK/"
            audit = json.loads(
                archive.read(prefix + "audit/D50_MIRROR_RECONCILIATION_AUDIT.json")
            )
            readme = archive.read(prefix + "README.txt").decode("utf-8")
        self.assertTrue(audit["candidate_only"])
        self.assertFalse(audit["runtime_mutation_performed"])
        self.assertIn("NOT an operational authorization", readme)
        self.assertIn("separately reviewed status-mirror update", readme)


if __name__ == "__main__":
    unittest.main()
