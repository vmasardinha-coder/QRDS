from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_2_prospective_counter_bridge import (
    STAGE9_COLLECTOR_ID,
    STAGE9_RAW_ROLES,
    SUPERVISOR_SAFETY,
    admission_content_hash,
)
from tools.gate_btc_2_stage9_admission_ledger import (
    append_admission,
    counter_from_ledger,
    parse_ledger,
    validate_ledger,
)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def admission(run_id: int, captured: str) -> dict:
    row = {
        "schema": "gate_btc.2_0.forward_capture_admission.v1",
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
        "captured_at_utc": captured,
        "capture_manifest_sha256": h(f"manifest-{run_id}"),
        "review_sha256": h(f"review-{run_id}"),
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "safety": SUPERVISOR_SAFETY,
    }
    row["admission_artifact_sha256"] = admission_content_hash(row)
    return row


class Stage9AdmissionLedgerTests(unittest.TestCase):
    def test_empty_ledger_is_valid_and_counter_zero(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            rows = parse_ledger(path)
            validate_ledger(rows)
            counter = counter_from_ledger(rows)
            self.assertEqual(counter["canonical_counter"], 0)
            self.assertEqual(counter["prospective_credit_from_backfill"], 0)

    def test_two_forward_admissions_append_and_count_two(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            first = append_admission(path, admission(1001, "2026-08-28T12:00:00Z"))
            before = path.read_bytes()
            second = append_admission(path, admission(1002, "2026-08-28T13:00:00Z"))
            after = path.read_bytes()
            self.assertTrue(after.startswith(before))
            self.assertEqual(first["sequence"], 1)
            self.assertEqual(first["previous_record_sha256"], "GENESIS")
            self.assertEqual(second["sequence"], 2)
            self.assertEqual(second["previous_record_sha256"], first["record_sha256"])
            rows = parse_ledger(path)
            validate_ledger(rows)
            self.assertEqual(counter_from_ledger(rows)["canonical_counter"], 2)

    def test_duplicate_run_is_rejected_without_changing_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            append_admission(path, admission(1001, "2026-08-28T12:00:00Z"))
            before = path.read_bytes()
            with self.assertRaises(RuntimeError):
                append_admission(path, admission(1001, "2026-08-28T13:00:00Z"))
            self.assertEqual(path.read_bytes(), before)

    def test_non_monotonic_capture_clock_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            append_admission(path, admission(1001, "2026-08-28T13:00:00Z"))
            with self.assertRaises(RuntimeError):
                append_admission(path, admission(1002, "2026-08-28T12:00:00Z"))

    def test_historical_line_mutation_breaks_chain(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            append_admission(path, admission(1001, "2026-08-28T12:00:00Z"))
            append_admission(path, admission(1002, "2026-08-28T13:00:00Z"))
            rows = parse_ledger(path)
            rows[0]["captured_at_utc"] = "2026-08-28T11:59:59Z"
            path.write_text("\n".join(json.dumps(r, separators=(",", ":"), sort_keys=True) for r in rows) + "\n")
            with self.assertRaises(RuntimeError):
                validate_ledger(parse_ledger(path))

    def test_removed_first_line_breaks_sequence_and_chain(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            append_admission(path, admission(1001, "2026-08-28T12:00:00Z"))
            append_admission(path, admission(1002, "2026-08-28T13:00:00Z"))
            rows = parse_ledger(path)
            path.write_text(json.dumps(rows[1], separators=(",", ":"), sort_keys=True) + "\n")
            with self.assertRaises(RuntimeError):
                validate_ledger(parse_ledger(path))

    def test_forked_previous_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            append_admission(path, admission(1001, "2026-08-28T12:00:00Z"))
            append_admission(path, admission(1002, "2026-08-28T13:00:00Z"))
            rows = parse_ledger(path)
            rows[1]["previous_record_sha256"] = "0" * 64
            path.write_text("\n".join(json.dumps(r, separators=(",", ":"), sort_keys=True) for r in rows) + "\n")
            with self.assertRaises(RuntimeError):
                validate_ledger(parse_ledger(path))

    def test_mutated_embedded_admission_is_rejected_even_if_outer_record_edited(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "stage9.jsonl"
            append_admission(path, admission(1001, "2026-08-28T12:00:00Z"))
            rows = parse_ledger(path)
            row = copy.deepcopy(rows[0])
            row["admission"]["captured_at_utc"] = "2026-08-28T12:01:00Z"
            # Deliberately leave admission self-hash stale. Even a rewritten outer record
            # cannot make an invalid admission eligible for prospective credit.
            row["record_sha256"] = "0" * 64
            path.write_text(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
            with self.assertRaises(RuntimeError):
                validate_ledger(parse_ledger(path))


if __name__ == "__main__":
    unittest.main()
