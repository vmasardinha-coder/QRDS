import copy
import unittest

from tools.gate_btc_2_temporal_causality_audit import (
    BLOCKED,
    PASS,
    audit_synthetic_trace,
    synthetic_trace,
)


BASELINE_SHA = "5e899984aef868961e2b768f9a0d0c277abce05d"


def codes(result):
    return {item["code"] for item in result["violations"]}


class GateBTC2TemporalCausalityAuditTests(unittest.TestCase):
    def test_clean_recursive_trace_passes_only_synthetic_conformance(self):
        result = audit_synthetic_trace(synthetic_trace(), BASELINE_SHA)
        self.assertEqual(result["status"], PASS)
        self.assertEqual(result["violation_count"], 0)
        self.assertEqual(result["audit_scope"], "SYNTHETIC_TRACE_CONFORMANCE_ONLY")
        self.assertFalse(result["official_dataset_audited"])
        self.assertFalse(result["predictive_validity_established"])
        self.assertFalse(result["stage_5_core_audits_passed"])
        self.assertFalse(result["official_challenger_runs_allowed"])

    def test_future_availability_and_crossing_window_fail_closed(self):
        events = synthetic_trace()
        events[1]["available_at_utc"] = "2026-01-01T00:01:06Z"
        events[1]["feature_window_end_utc"] = "2026-01-01T00:01:07Z"
        result = audit_synthetic_trace(events, BASELINE_SHA)
        self.assertEqual(result["status"], BLOCKED)
        self.assertTrue({
            "LOOKAHEAD_AVAILABLE_AFTER_DECISION",
            "FEATURE_WINDOW_CROSSES_DECISION",
        }.issubset(codes(result)))

    def test_future_revision_and_sequence_regression_fail_closed(self):
        events = synthetic_trace()
        events[1]["revision_available_at_utc"] = "2026-01-01T00:01:08Z"
        events[2]["decision_timestamp_utc"] = "2026-01-01T00:00:30Z"
        result = audit_synthetic_trace(events, BASELINE_SHA)
        self.assertEqual(result["status"], BLOCKED)
        self.assertIn("FUTURE_SOURCE_REVISION", codes(result))
        self.assertIn("DECISION_SEQUENCE_REGRESSION", codes(result))
        self.assertIn("PARENT_DECIDED_AFTER_CHILD", codes(result))

    def test_cycle_and_missing_parent_are_detected(self):
        events = synthetic_trace()
        events[0]["parent_event_id"] = "derived-0002"
        events[0]["recursion_depth"] = 2
        events[2]["parent_event_id"] = "absent-event"
        result = audit_synthetic_trace(events, BASELINE_SHA)
        self.assertEqual(result["status"], BLOCKED)
        self.assertIn("RECURSION_CYCLE", codes(result))
        self.assertIn("PARENT_EVENT_MISSING", codes(result))

    def test_non_utc_duplicate_and_unsafe_fields_fail_closed(self):
        events = synthetic_trace()
        duplicate = copy.deepcopy(events[1])
        duplicate["decision_timestamp_utc"] = "2026-01-01T03:01:05+03:00"
        duplicate["orders_generated"] = 1
        events.append(duplicate)
        result = audit_synthetic_trace(events, BASELINE_SHA)
        self.assertEqual(result["status"], BLOCKED)
        self.assertIn("DUPLICATE_EVENT_ID", codes(result))
        self.assertIn("TIMESTAMP_NOT_UTC", codes(result))
        self.assertIn("UNSAFE_EVENT_FIELD", codes(result))
        self.assertEqual(result["safety"]["orders_generated"], 0)
        self.assertEqual(result["safety"]["real_capital_used"], 0)

    def test_result_hash_is_deterministic_and_trace_bound(self):
        first = audit_synthetic_trace(synthetic_trace(), BASELINE_SHA)
        second = audit_synthetic_trace(synthetic_trace(), BASELINE_SHA)
        self.assertEqual(first["audit_sha256"], second["audit_sha256"])
        mutated = synthetic_trace()
        mutated[0]["input_sha256"] = "f" * 64
        changed = audit_synthetic_trace(mutated, BASELINE_SHA)
        self.assertNotEqual(first["trace_sha256"], changed["trace_sha256"])
        self.assertNotEqual(first["audit_sha256"], changed["audit_sha256"])


if __name__ == "__main__":
    unittest.main()
