import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_d50_status_align import build_alignment


class D50StatusAlignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.measurement = self.root / "measurement.json"
        self.remote = self.root / "remote.json"
        self.measurement.write_text(json.dumps({
            "reconciliation_note": "verified local evidence",
            "d50_prospective_immutable_ledger": {
                "current": 13,
                "target": 30,
                "status": "ACTIVE",
                "latest_prospective_date": "2026-08-14",
                "source_hashes": {"ohlc": "a" * 64, "funding": "b" * 64},
                "user_action_required": False,
            },
            "d50_data_qualification": {
                "current": 4,
                "target": 7,
                "snapshot_count_total": 14,
                "hash_chain_valid": True,
                "user_action_required": False,
            },
        }), encoding="utf-8")
        self.remote.write_text(json.dumps({
            "prospective_immutable_ledger": {"current": 4},
        }), encoding="utf-8")
        self.daily = []
        self.readiness = []
        prior = "p" * 64
        for total, consecutive, day, digest in (
            (12, 2, "2026-08-12", "c" * 64),
            (13, 3, "2026-08-13", "d" * 64),
            (14, 4, "2026-08-14", "e" * 64),
        ):
            snapshot = {
                "snapshot_id": day,
                "snapshot_sha256": digest,
                "previous_snapshot_sha256": prior,
                "qualification_pass": True,
                "coverage_pct": 1.0,
                "fresh_count": 20,
                "universe_size": 20,
            }
            qualification = {
                "snapshot_count_total": total,
                "latest_consecutive_pass_count": consecutive,
                "hash_chain_valid": True,
            }
            daily = self.root / f"daily-{day}.txt"
            daily.write_text(
                "ORDERS_GENERATED=0\nREAL_CAPITAL_USED=0\n"
                + json.dumps({"status": "PASS", "result": {"snapshot": snapshot}})
                + "\nSTATUS=PASS\n",
                encoding="utf-8",
            )
            ready = self.root / f"ready-{day}.txt"
            ready.write_text(
                "STATUS=PASS\nRESULT_JSON="
                + json.dumps({"snapshot": snapshot, "qualification": qualification})
                + "\n",
                encoding="utf-8",
            )
            self.daily.append(daily)
            self.readiness.append(ready)
            prior = digest

    def tearDown(self):
        self.temp.cleanup()

    def test_aligns_only_stale_status_mirror(self):
        status, audit = build_alignment(
            measurement_path=self.measurement,
            remote_status_path=self.remote,
            daily_reports=self.daily,
            readiness_reports=self.readiness,
        )
        self.assertEqual(status["prospective_immutable_ledger"]["current"], 13)
        self.assertEqual(status["data_qualification"]["current"], 4)
        self.assertEqual(status["data_qualification"]["latest_snapshot_id"], "2026-08-14")
        self.assertTrue(status["prospective_immutable_ledger"]["mirror_alignment_only"])
        self.assertEqual(audit["economic_rows_imported"], 0)
        self.assertEqual(audit["economic_rows_mutated"], 0)

    def test_rejects_broken_attached_hash_chain(self):
        for path in (self.daily[-1], self.readiness[-1]):
            payload = path.read_text(encoding="utf-8")
            path.write_text(payload.replace("d" * 64, "f" * 64), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "hash chain"):
            build_alignment(
                measurement_path=self.measurement,
                remote_status_path=self.remote,
                daily_reports=self.daily,
                readiness_reports=self.readiness,
            )


if __name__ == "__main__":
    unittest.main()
