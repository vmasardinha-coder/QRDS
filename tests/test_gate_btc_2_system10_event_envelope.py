from __future__ import annotations

import hashlib
import unittest

from tools.gate_btc_2_prospective_counter_bridge import STAGE9_RAW_ROLES, SUPERVISOR_SAFETY, admission_content_hash
from tools.gate_btc_2_stage9_admission_ledger import make_record
from tools.gate_btc_2_system10_event_envelope import build_event_envelope, verify_event_envelope


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def admission(run_id: int, captured: str) -> dict:
    row = {
        "schema": "gate_btc.2_0.forward_capture_admission.v1",
        "collector_id": "GATE_BTC_2_STAGE9_MICROSTRUCTURE",
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


class System10EventEnvelopeTests(unittest.TestCase):
    def test_empty_ledger_emits_zero_event_safe_envelope(self):
        envelope = build_event_envelope([])
        verify_event_envelope(envelope)
        self.assertEqual(envelope["event_count"], 0)
        self.assertFalse(envelope["stage_9_complete"])
        self.assertFalse(envelope["system_10_complete"])
        self.assertFalse(envelope["engine_feed"])
        self.assertEqual(envelope["orders"], 0)
        self.assertEqual(envelope["real_capital_brl"], 0)

    def test_admitted_records_map_one_to_one(self):
        a1 = admission(1001, "2026-08-28T12:00:00Z")
        a2 = admission(1002, "2026-08-28T13:00:00Z")
        r1 = make_record(a1, 1, "GENESIS")
        r2 = make_record(a2, 2, r1["record_sha256"])
        envelope = build_event_envelope([r1, r2])
        verify_event_envelope(envelope)
        self.assertEqual(envelope["event_count"], 2)
        self.assertEqual(envelope["events"][0]["run_id"], 1001)
        self.assertEqual(envelope["events"][1]["run_id"], 1002)
        self.assertTrue(all(e["engine_neutral"] for e in envelope["events"]))
        self.assertTrue(all(not e["nautilus_execution_enabled"] for e in envelope["events"]))

    def test_tamper_is_rejected(self):
        a1 = admission(1001, "2026-08-28T12:00:00Z")
        r1 = make_record(a1, 1, "GENESIS")
        envelope = build_event_envelope([r1])
        envelope["events"][0]["run_id"] = 9999
        with self.assertRaises(RuntimeError):
            verify_event_envelope(envelope)


if __name__ == "__main__":
    unittest.main()
