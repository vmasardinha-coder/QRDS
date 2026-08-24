import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_d50_delivery_replay import build_delivery_replay


def write_daily(path: Path, snapshot: dict, qualification: dict) -> None:
    payload = {"status": "PASS", "result": {"snapshot": snapshot, "qualification": qualification}}
    path.write_text(
        "ORDERS_GENERATED=0\nREAL_CAPITAL_USED=0\n"
        + json.dumps(payload)
        + "\nSTATUS=PASS\n",
        encoding="utf-8",
    )


def write_readiness(path: Path, snapshot: dict, qualification: dict) -> None:
    path.write_text(
        "ORDERS_GENERATED=0\nREAL_CAPITAL_USED=0\nSTATUS=PASS\nRESULT_JSON="
        + json.dumps({"snapshot": snapshot, "qualification": qualification})
        + "\n",
        encoding="utf-8",
    )


def write_economic(path: Path, current: int, day: str) -> None:
    payload = {
        "status": "PASS_PROSPECTIVE_ROWS_APPENDED",
        "d50_ingestion_gate": "PASS",
        "new_paired_observations": 1,
        "paired_prospective_observations": current,
        "first_prospective_date": "2026-07-31",
        "latest_prospective_date": day,
        "excluded_historical_backfill_dates": ["2026-08-04", "2026-08-05"],
        "historical_backfill_counted_as_prospective": False,
        "checkpoint_due": False,
        "next_checkpoint": 30,
        "source_hashes": {"ohlc": "1" * 64, "funding": "2" * 64},
        "research_only": True,
        "orders": 0,
        "capital": 0,
    }
    path.write_text(
        "STATUS=PASS_DAILY_UPDATE\nRESEARCH_ONLY=True\nORDERS=0\nCAPITAL=0\n"
        "STEP_BEGIN=APPEND_ONLY_ADMISSIBLE_BAR\n"
        + json.dumps(payload)
        + "\nSTEP_END=APPEND_ONLY_ADMISSIBLE_BAR EXIT_CODE=0\n",
        encoding="utf-8",
    )


class D50DeliveryReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.measurement = self.root / "measurement.json"
        self.remote = self.root / "status.json"
        base_ledger = {
            "current": 14,
            "target": 30,
            "status": "ACTIVE",
            "first_prospective_date": "2026-07-31",
            "latest_prospective_date": "2026-08-15",
            "excluded_historical_backfill_dates": ["2026-08-04", "2026-08-05"],
            "historical_backfill_counts_as_prospective": False,
            "frozen_history_must_be_preserved": True,
            "mutation_performed": False,
            "user_action_required": False,
            "source_hashes": {"ohlc": "a" * 64, "funding": "b" * 64},
        }
        base_qualification = {
            "current": 0,
            "target": 7,
            "snapshot_count_total": 15,
            "latest_snapshot_id": "2026-08-15",
            "latest_snapshot_sha256": "a" * 64,
            "hash_chain_valid": True,
            "user_action_required": False,
        }
        safety = {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "promotion_allowed": False,
            "orders_generated": 0,
            "real_capital_used": 0,
        }
        self.remote.write_text(
            json.dumps(
                {
                    "schema": "gate_btc.d50_measurement_status.v1",
                    "data_as_of": "2026-08-15",
                    "prospective_immutable_ledger": base_ledger,
                    "data_qualification": base_qualification,
                    **safety,
                }
            ),
            encoding="utf-8",
        )
        self.measurement.write_text(
            json.dumps(
                {
                    "schema": "gate_btc.measurement_status.v1",
                    "data_as_of": "2026-08-15",
                    "d50_prospective_immutable_ledger": base_ledger,
                    "d50_data_qualification": base_qualification,
                    "d50_reconciliation": {"status": "PASS_BASE", "alignment_sha256": "c" * 64},
                    "reconciliation_note": "verified base",
                    **safety,
                }
            ),
            encoding="utf-8",
        )
        self.base_daily = self.root / "daily-15.txt"
        self.base_ready = self.root / "ready-15.txt"
        base_snapshot = self.snapshot("2026-08-15", 15, 0, "a" * 64, "9" * 64, False)
        base_qual = self.qualification(15, 0, False)
        write_daily(self.base_daily, base_snapshot, base_qual)
        write_readiness(self.base_ready, base_snapshot, base_qual)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def snapshot(day, total, consecutive, digest, previous, passed):
        return {
            "snapshot_id": day,
            "snapshot_sha256": digest,
            "previous_snapshot_sha256": previous,
            "qualification_pass": passed,
            "synchronized_failure": not passed,
            "coverage_pct": 1.0 if passed else 0.0,
            "fresh_count": 20 if passed else 0,
            "universe_size": 20,
            "observations": [],
        }

    @staticmethod
    def qualification(total, consecutive, qualified):
        return {
            "snapshot_count_total": total,
            "latest_consecutive_pass_count": consecutive,
            "hash_chain_valid": True,
            "qualified": qualified,
        }

    def step(self, day, total, consecutive, digest, previous, economic_current):
        daily = self.root / f"daily-{day}.txt"
        ready = self.root / f"ready-{day}.txt"
        economic = self.root / f"economic-{day}.txt"
        snap = self.snapshot(day, total, consecutive, digest, previous, True)
        qual = self.qualification(total, consecutive, consecutive >= 7)
        write_daily(daily, snap, qual)
        write_readiness(ready, snap, qual)
        write_economic(economic, economic_current, day)
        return daily, ready, economic

    def test_replays_multiple_exact_forward_steps_without_mutating_sources(self):
        first = self.step("2026-08-16", 16, 1, "b" * 64, "a" * 64, 15)
        second = self.step("2026-08-17", 17, 2, "c" * 64, "b" * 64, 16)
        inputs = [self.measurement, self.remote, self.base_daily, self.base_ready, *first, *second]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}

        status, measurement, audit = build_delivery_replay(
            measurement_path=self.measurement,
            remote_status_path=self.remote,
            base_daily_report=self.base_daily,
            base_readiness_report=self.base_ready,
            evidence_steps=[first, second],
        )

        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
        self.assertEqual(before, after)
        self.assertEqual(status["prospective_immutable_ledger"]["current"], 16)
        self.assertEqual(status["data_qualification"]["current"], 2)
        self.assertEqual(status["data_qualification"]["snapshot_count_total"], 17)
        self.assertEqual(measurement["d50_prospective_immutable_ledger"]["current"], 16)
        self.assertEqual(audit["status"], "PASS_FORWARD_ONLY_D50_DELIVERY_RECONCILIATION")
        self.assertEqual(len(audit["transitions"]), 2)
        self.assertEqual(audit["economic_rows_imported"], 0)
        self.assertEqual(audit["economic_rows_mutated"], 0)
        self.assertFalse(audit["historical_or_retroactive_fill_used"])
        self.assertFalse(audit["runtime_branch_mutation_performed"])

    def test_rejects_gap_in_qualification_chain(self):
        bad = self.step("2026-08-17", 17, 1, "c" * 64, "a" * 64, 15)
        with self.assertRaisesRegex(RuntimeError, "snapshot counter is not consecutive"):
            build_delivery_replay(
                measurement_path=self.measurement,
                remote_status_path=self.remote,
                base_daily_report=self.base_daily,
                base_readiness_report=self.base_ready,
                evidence_steps=[bad],
            )

    def test_rejects_economic_counter_jump(self):
        bad = self.step("2026-08-16", 16, 1, "b" * 64, "a" * 64, 16)
        with self.assertRaisesRegex(RuntimeError, "append count does not extend the published tip"):
            build_delivery_replay(
                measurement_path=self.measurement,
                remote_status_path=self.remote,
                base_daily_report=self.base_daily,
                base_readiness_report=self.base_ready,
                evidence_steps=[bad],
            )

    def test_checkpoint5_decision_preserves_fail_closed_boundary(self):
        decision_path = (
            Path(__file__).resolve().parents[1]
            / "tools"
            / "gate_btc_d50_checkpoint5_decision_v1.json"
        )
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        self.assertEqual(
            decision["decision"],
            "PASS_LOCAL_FORWARD_ONLY_RECONCILIATION_RUNTIME_PUBLICATION_PENDING",
        )
        self.assertEqual(decision["runtime_base"]["economic"], "14/30")
        self.assertEqual(decision["candidate_runtime"]["economic"], "21/30")
        self.assertEqual(decision["candidate_runtime"]["qualification"], "7/7")
        self.assertEqual(decision["candidate_runtime"]["publication_status"], "PENDING_EXPLICIT_EXTERNAL_WRITE_APPROVAL")
        self.assertEqual(decision["non_interference"]["economic_rows_imported"], 0)
        self.assertEqual(decision["non_interference"]["economic_rows_mutated"], 0)
        self.assertFalse(decision["non_interference"]["historical_or_retroactive_fill_used"])
        self.assertEqual(
            decision["interpretation"]["collection_health"], "RED_STALE"
        )
        self.assertEqual(
            decision["safety"],
            {
                "RESEARCH_ONLY": True,
                "SHADOW_ONLY": True,
                "NOT_APPROVED": True,
                "ENGINE_FEED": False,
                "ORDERS": 0,
                "REAL_CAPITAL": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
