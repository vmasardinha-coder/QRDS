import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tools import gate_btc_bull_replay_live_shadow as bull
from tools import gate_btc_bull_replay_delivery_audit as audit


class DeliveryAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "ANCHOR.json").write_text(
            json.dumps({"anchor_date": "2026-08-13"}) + "\n", encoding="utf-8")
        rows = []
        previous = bull.ZERO_HASH
        for series in (*bull.REQUIRED_V2A, *bull.REQUIRED_DELTA):
            row = dict(date="2026-08-14", series=series,
                       source_family="V2A_PUBLISHED_EQUITY" if series in bull.REQUIRED_V2A else "DELTA_PUBLISHED_DAILY",
                       gross_return="0", net_return="0", gross_nav="1", net_nav="1",
                       source_run_id="123", source_data_as_of="2026-08-14",
                       source_v2a_sha256="a" * 64, source_delta_sha256="b" * 64,
                       prev_hash=previous)
            row["row_hash"] = bull.hash_row(row)
            previous = row["row_hash"]
            rows.append(row)
        bull.write_ledger(self.root / "DAILY_LEDGER.csv", rows)
        (self.root / "STATUS.json").write_text(
            json.dumps({"status": "LIVE_DIAGNOSTIC_ACTIVE",
                        "leaderboard_descriptive_only": [{"series": "Victor_proxy"}],
                        "research_only": True, "shadow_only": True,
                        "not_approved": True, "orders_generated": 0,
                        "real_capital_used": 0}) + "\n", encoding="utf-8")

    def test_interrupt_preserve_and_idempotence(self):
        old = {name: (self.root / name).read_bytes()
               for name in ("ANCHOR.json", "DAILY_LEDGER.csv", "STATUS.json")}
        at = datetime(2026, 9, 29, tzinfo=timezone.utc)
        result = audit.audit(self.root, at)
        self.assertFalse(result["can_append"])
        self.assertEqual(result["scientific_credit"], 0)
        self.assertEqual(result["observed_days"], 1)
        self.assertEqual(result["leaderboard_descriptive_only"][0]["series"], "Victor_proxy")
        self.assertEqual((self.root / "preserved/STATUS_BEFORE_REPAIR.json").read_bytes(), old["STATUS.json"])
        for name in ("ANCHOR.json", "DAILY_LEDGER.csv"):
            self.assertEqual((self.root / name).read_bytes(), old[name])
        again = audit.audit(self.root, at)
        self.assertEqual(again["status"], result["status"])
        self.assertEqual(json.loads((self.root / "STATUS.json").read_text())["status"], result["status"])

    def test_seal_rejects_changed_original(self):
        audit.audit(self.root, datetime(2026, 9, 29, tzinfo=timezone.utc))
        with (self.root / "DAILY_LEDGER.csv").open("a", encoding="utf-8") as file:
            file.write("mutation")
        with self.assertRaises(ValueError):
            audit.audit(self.root, datetime(2026, 9, 29, tzinfo=timezone.utc))
