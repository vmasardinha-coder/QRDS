from __future__ import annotations

import hashlib
import unittest
from datetime import datetime, timedelta, timezone

from tools.gate_btc_2_prospective_counter_bridge import (
    SCHEMA_ADMISSION,
    STAGE9_COLLECTOR_ID,
    STAGE9_RAW_ROLES,
    SUPERVISOR_SAFETY,
    admission_content_hash,
)
from tools.gate_btc_2_stage9_admission_ledger import GENESIS, make_record
from tools.gate_btc_2_stage9_exit_gate import evaluate, load_prereg, verify_status


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def admission(run_id: int, dt: datetime) -> dict:
    row = {
        "schema": SCHEMA_ADMISSION,
        "collector_id": STAGE9_COLLECTOR_ID,
        "decision": "ADMITTED_FORWARD_ONLY",
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "instrument": "BTCUSDT",
        "raw_roles": list(STAGE9_RAW_ROLES),
        "run_id": run_id,
        "captured_at_utc": iso(dt),
        "capture_manifest_sha256": h(f"manifest-{run_id}"),
        "review_sha256": h(f"review-{run_id}"),
        "safety": SUPERVISOR_SAFETY,
    }
    row["admission_artifact_sha256"] = admission_content_hash(row)
    return row


def ledger(start: datetime, count: int, run_start: int = 1000) -> list[dict]:
    rows = []
    previous = GENESIS
    for i in range(count):
        adm = admission(run_start + i, start + timedelta(hours=i))
        rec = make_record(adm, i + 1, previous)
        rows.append(rec)
        previous = rec["record_sha256"]
    return rows


class Stage9ExitGateTests(unittest.TestCase):
    def setUp(self):
        self.prereg = load_prereg()

    def test_pre_activation_records_receive_zero_exit_credit(self):
        rows = ledger(datetime(2026, 9, 5, 0, tzinfo=timezone.utc), 50)
        status = evaluate(rows, self.prereg)
        verify_status(status)
        self.assertEqual(status["original_stage9_canonical_counter"], 50)
        self.assertEqual(status["exit_segment"]["current_N"], 0)
        self.assertEqual(status["pre_activation_exit_credit"], 0)
        self.assertFalse(status["stage_9_complete"])

    def test_167_eligible_hours_remain_collect_more(self):
        rows = ledger(datetime(2026, 9, 8, 0, tzinfo=timezone.utc), 167)
        status = evaluate(rows, self.prereg)
        verify_status(status)
        self.assertEqual(status["decision"], "COLLECT_MORE_FORWARD_EVIDENCE")
        self.assertEqual(status["exit_segment"]["current_N"], 167)
        self.assertFalse(status["exit_segment"]["checks"]["required_N"])
        self.assertFalse(status["stage_9_complete"])

    def test_exact_full_week_passes_exit_gate(self):
        rows = ledger(datetime(2026, 9, 8, 0, tzinfo=timezone.utc), 168)
        status = evaluate(rows, self.prereg)
        verify_status(status)
        self.assertEqual(status["decision"], "PASS_STAGE9_EXIT_GATE")
        self.assertEqual(status["exit_segment"]["current_N"], 168)
        self.assertEqual(len(status["exit_segment"]["distinct_utc_hours"]), 24)
        self.assertEqual(len(status["exit_segment"]["distinct_utc_weekdays"]), 7)
        self.assertEqual(status["exit_segment"]["elapsed_hours"], 167.0)
        self.assertTrue(status["stage_9_complete"])
        self.assertTrue(status["completion_effect"]["system_10_dependency_released_for_research_only_engine_parity"])
        self.assertFalse(status["completion_effect"]["engine_feed"])
        self.assertEqual(status["completion_effect"]["orders"], 0)
        self.assertEqual(status["completion_effect"]["real_capital"], 0)

    def test_168_records_without_full_weekday_coverage_fail(self):
        # 168 distinct records compressed into six weekdays by stepping 30 minutes;
        # count alone cannot satisfy structural coverage.
        rows = []
        previous = GENESIS
        start = datetime(2026, 9, 8, 0, tzinfo=timezone.utc)
        for i in range(168):
            dt = start + timedelta(minutes=30 * i)
            adm = admission(5000 + i, dt)
            rec = make_record(adm, i + 1, previous)
            rows.append(rec)
            previous = rec["record_sha256"]
        status = evaluate(rows, self.prereg)
        verify_status(status)
        self.assertFalse(status["stage_9_complete"])
        self.assertFalse(status["exit_segment"]["checks"]["utc_weekday_coverage"])
        self.assertFalse(status["exit_segment"]["checks"]["elapsed_hours"])


if __name__ == "__main__":
    unittest.main()
