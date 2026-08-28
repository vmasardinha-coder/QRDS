from __future__ import annotations

import hashlib
import unittest

from tools.gate_btc_2_evidence_factory import SAFETY, SCHEMA_CANDIDATE
from tools.gate_btc_2_prospective_counter_bridge import STAGE9_RAW_ROLES, SUPERVISOR_SAFETY, admission_content_hash
from tools.gate_btc_2_stage9_a4_projection import project
from tools.gate_btc_2_stage9_admission_ledger import make_record


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def candidate() -> dict:
    return {
        "schema": SCHEMA_CANDIDATE,
        "candidate_id": "H-STAGE9-PROJECTION-TEST",
        "candidate_version": 1,
        "hypothesis_sha256": h("hypothesis"),
        "config_sha256": h("config"),
        "code_sha256": h("code"),
        "cutoff_utc": "2026-08-27T00:00:00Z",
        "d0_utc": "2026-08-28T00:00:00Z",
        "source_identity": {"venue": "frozen-public-source"},
        "strategy_factory_artifact_sha256": h("factory"),
        "required_evidence": ["PROSPECTIVE"],
        "safety": SAFETY,
    }


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


class Stage9A4ProjectionTests(unittest.TestCase):
    def test_empty_ledger_is_collect_more_zero_credit(self):
        out = project(candidate(), [], 3, "2026-09-01")
        self.assertEqual(out["decision"], "COLLECT_MORE")
        self.assertEqual(out["current_N"], 0)
        self.assertEqual(out["remaining_N"], 3)
        self.assertEqual(out["prospective_credit_from_backfill"], 0)
        self.assertFalse(out["stage_9_complete"])
        self.assertFalse(out["economics_allowed"])
        self.assertFalse(out["engine_feed"])
        self.assertEqual(out["orders"], 0)
        self.assertEqual(out["real_capital_brl"], 0)
        self.assertEqual(out["executive_items"]["6"]["status"], "COLLECT_MORE")

    def test_valid_admitted_ledger_advances_count_only(self):
        a1 = admission(1001, "2026-08-28T12:00:00Z")
        r1 = make_record(a1, 1, "GENESIS")
        out = project(candidate(), [r1], 2, "2026-09-01")
        self.assertEqual(out["current_N"], 1)
        self.assertEqual(out["remaining_N"], 1)
        self.assertEqual(out["decision"], "COLLECT_MORE")
        self.assertFalse(out["stage_9_complete"])

    def test_required_counter_pass_does_not_claim_stage_completion_or_economics(self):
        a1 = admission(1001, "2026-08-28T12:00:00Z")
        r1 = make_record(a1, 1, "GENESIS")
        out = project(candidate(), [r1], 1, "2026-08-28")
        self.assertEqual(out["decision"], "PASS_COUNTER_REQUIREMENT")
        self.assertEqual(out["next_state"], "PROSPECTIVE_EVIDENCE")
        self.assertFalse(out["stage_9_complete"])
        self.assertFalse(out["economics_allowed"])
        self.assertFalse(out["automatic_promotion"])
        self.assertEqual(out["orders"], 0)
        self.assertEqual(out["real_capital_brl"], 0)

    def test_invalid_required_n_fails_closed(self):
        for n in (0, -1, True):
            with self.assertRaises(RuntimeError):
                project(candidate(), [], n, "2026-09-01")


if __name__ == "__main__":
    unittest.main()
