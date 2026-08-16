import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_d50_status_align import build_alignment, build_measurement_alignment


class D50StatusAlignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.measurement = self.root / "measurement.json"
        self.remote = self.root / "remote.json"
        self.measurement.write_text(json.dumps({
            "reconciliation_note": "verified local evidence",
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "promotion_allowed": False,
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
                "ORDERS_GENERATED=0\nREAL_CAPITAL_USED=0\nSTATUS=PASS\nRESULT_JSON="
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

    def _add_failed_snapshot_pair(self, suffix: str):
        snapshot = {
            "snapshot_id": "2026-08-15",
            "snapshot_sha256": "f" * 64,
            "previous_snapshot_sha256": "e" * 64,
            "qualification_pass": False,
            "synchronized_failure": True,
            "coverage_pct": 0.0,
            "fresh_count": 0,
            "universe_size": 20,
        }
        qualification = {
            "snapshot_count_total": 15,
            "latest_consecutive_pass_count": 0,
            "hash_chain_valid": True,
            "qualified": False,
        }
        daily = self.root / f"daily-{suffix}.txt"
        daily.write_text(
            "ORDERS_GENERATED=0\nREAL_CAPITAL_USED=0\n"
            + json.dumps({"status": "PASS", "result": {"snapshot": snapshot}})
            + "\nSTATUS=PASS\n",
            encoding="utf-8",
        )
        ready = self.root / f"ready-{suffix}.txt"
        ready.write_text(
            "ORDERS_GENERATED=0\nREAL_CAPITAL_USED=0\nSTATUS=PASS\nRESULT_JSON="
            + json.dumps({"snapshot": snapshot, "qualification": qualification})
            + "\n",
            encoding="utf-8",
        )
        return daily, ready

    def _ledger_report(self):
        report = self.root / "d50-ledger.txt"
        append = {
            "status": "PASS_PROSPECTIVE_ROWS_APPENDED",
            "d50_ingestion_gate": "PASS",
            "new_paired_observations": 1,
            "paired_prospective_observations": 14,
            "first_prospective_date": "2026-07-31",
            "latest_prospective_date": "2026-08-15",
            "excluded_historical_backfill_dates": ["2026-08-04", "2026-08-05"],
            "historical_backfill_counted_as_prospective": False,
            "checkpoint_due": False,
            "next_checkpoint": 30,
            "source_hashes": {"ohlc": "1" * 64, "funding": "2" * 64},
            "research_only": True,
            "orders": 0,
            "capital": 0,
        }
        report.write_text(
            "STATUS=PASS_DAILY_UPDATE\nRESEARCH_ONLY=True\nORDERS=0\nCAPITAL=0\n"
            "STEP_BEGIN=APPEND_ONLY_ADMISSIBLE_BAR\n"
            + json.dumps(append)
            + "\nSTEP_END=APPEND_ONLY_ADMISSIBLE_BAR EXIT_CODE=0\n",
            encoding="utf-8",
        )
        return report

    def test_aligns_one_append_and_deduplicates_repeated_failed_snapshot(self):
        first_daily, first_ready = self._add_failed_snapshot_pair("2026-08-15-a")
        repeat_daily, repeat_ready = self._add_failed_snapshot_pair("2026-08-15-b")
        status, audit = build_alignment(
            measurement_path=self.measurement,
            remote_status_path=self.remote,
            daily_reports=self.daily + [first_daily, repeat_daily],
            readiness_reports=self.readiness + [first_ready, repeat_ready],
            ledger_report=self._ledger_report(),
        )
        self.assertEqual(status["prospective_immutable_ledger"]["current"], 14)
        self.assertEqual(status["prospective_immutable_ledger"]["latest_prospective_date"], "2026-08-15")
        self.assertEqual(status["data_qualification"]["current"], 0)
        self.assertTrue(status["data_qualification"]["synchronized_failure"])
        self.assertEqual(status["data_qualification"]["snapshot_count_total"], 15)
        self.assertEqual(len(audit["idempotent_duplicate_report_pairs"]), 1)
        self.assertFalse(audit["duplicate_reports_double_counted"])
        self.assertEqual(audit["economic_rows_appended_by_source_run"], 1)
        self.assertEqual(audit["economic_rows_imported"], 0)
        aggregate = build_measurement_alignment(
            json.loads(self.measurement.read_text(encoding="utf-8")), status, audit
        )
        self.assertEqual(aggregate["d50_prospective_immutable_ledger"]["current"], 14)
        self.assertEqual(aggregate["d50_data_qualification"]["current"], 0)
        self.assertIn("not double-counted", aggregate["reconciliation_note"])

    def test_rejects_conflicting_repeat_for_same_snapshot_id(self):
        first_daily, first_ready = self._add_failed_snapshot_pair("2026-08-15-a")
        repeat_daily, repeat_ready = self._add_failed_snapshot_pair("2026-08-15-b")
        for path in (repeat_daily, repeat_ready):
            path.write_text(path.read_text(encoding="utf-8").replace("f" * 64, "9" * 64), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "conflicting reports"):
            build_alignment(
                measurement_path=self.measurement,
                remote_status_path=self.remote,
                daily_reports=self.daily + [first_daily, repeat_daily],
                readiness_reports=self.readiness + [first_ready, repeat_ready],
                ledger_report=self._ledger_report(),
            )

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
