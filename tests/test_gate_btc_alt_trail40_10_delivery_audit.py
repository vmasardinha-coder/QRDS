import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tools import gate_btc_alt_trail40_10_shadow_archive as archive
from tools import gate_btc_alt_trail40_10_delivery_audit as audit


class DeliveryAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "ledger"
        archive.initialize(audit.CONTRACT, self.root)
        self.anchor = (self.root / "ANCHOR.json").read_bytes()
        row = {
            "snapshot_date": "2026-08-31", "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
            "contract_sha256": archive.file_sha(audit.CONTRACT), "previous_row_sha256": None,
            "signals": {}, "selected_alt_closes": {}, "research_only": True,
            "engine_feed": False, "orders_generated": 0, "real_capital_used": 0}
        row["row_sha256"] = archive.payload_sha(row, "row_sha256")
        archive.write_json(self.root / "snapshots/2026-08-31.json", row)
        archive.write_json(self.root / "EVALUATION.json", {"decision": "WAITING_PROSPECTIVE_GATE"})
        self.snapshot = (self.root / "snapshots/2026-08-31.json").read_bytes()
        self.evaluation = (self.root / "EVALUATION.json").read_bytes()
        self.at = datetime(2026, 9, 28, 23, tzinfo=timezone.utc)

    def test_seals_missing_entry_without_credit_and_is_idempotent(self):
        first = audit.audit(self.root, self.at)
        self.assertEqual(first["status"], "BLOCKED_INDEPENDENT_MONTHLY_CYCLE_AUTHORIZATION_REQUIRED")
        self.assertEqual(first["reason"], "MISSING_CONFIRMED_FIRST_ENTRY_CLOSE_NO_BACKFILL")
        self.assertEqual(first["economic_credit"], 0)
        self.assertFalse(first["can_append"])
        self.assertEqual(audit.audit(self.root, self.at)["reason"], first["reason"])
        self.assertEqual((self.root / "ANCHOR.json").read_bytes(), self.anchor)
        self.assertEqual((self.root / "snapshots/2026-08-31.json").read_bytes(), self.snapshot)
        self.assertEqual((self.root / "EVALUATION.json").read_bytes(), self.evaluation)
        self.assertEqual(len(archive.snapshot_paths(self.root)), 1)
        with self.assertRaisesRegex(RuntimeError, "interrupted history"):
            archive.append(audit.CONTRACT, self.root, "none", "none", "2026-09-01", "2")

    def test_seal_rejects_changed_original(self):
        audit.audit(self.root, self.at)
        (self.root / "EVALUATION.json").write_text('{"decision":"changed"}')
        with self.assertRaisesRegex(ValueError, "INTERRUPTED_EVIDENCE_CHANGED"):
            audit.audit(self.root, self.at)


if __name__ == "__main__":
    unittest.main()
