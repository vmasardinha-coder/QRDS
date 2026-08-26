import unittest

from tools.gate_btc_factory.operational_repair_loop import decide


class OperationalRepairLoopTests(unittest.TestCase):
    def test_allowlisted_incident_gets_one_safe_retry(self):
        status = {"repair_scope": "ORCHESTRATION_AND_DATA_DELIVERY_ONLY", "data_as_of": "2026-08-25"}
        out = decide(status, {"status": "REFERENCE_CALENDAR_READY"}, 1)
        self.assertEqual(out["decision"], "SAFE_MECHANICAL_RETRY_ONCE")
        self.assertTrue(out["safe_retry"])
        self.assertFalse(out["methodology_changes_allowed"])

    def test_true_data_gap_never_retries(self):
        status = {"repair_scope": "ORCHESTRATION_AND_DATA_DELIVERY_ONLY", "data_as_of": "2026-08-25"}
        out = decide(status, {"status": "DATA_GAP", "reason": "BTC_CUTOFF_ABSENT"}, 1)
        self.assertEqual(out["decision"], "FAIL_CLOSED_DATA_GAP")
        self.assertFalse(out["safe_retry"])

    def test_second_failure_escalates_human(self):
        status = {"repair_scope": "ORCHESTRATION_AND_DATA_DELIVERY_ONLY"}
        out = decide(status, None, 2)
        self.assertEqual(out["decision"], "FAIL_CLOSED_HUMAN_ESCALATION")
        self.assertFalse(out["safe_retry"])
        self.assertTrue(out["escalate_human"])

    def test_non_allowlisted_scope_is_never_touched(self):
        out = decide({"repair_scope": "SCIENTIFIC_METHOD_CHANGE"}, None, 1)
        self.assertEqual(out["decision"], "NO_AUTOREPAIR_OUTSIDE_ALLOWLIST")
        self.assertFalse(out["safe_retry"])


if __name__ == "__main__":
    unittest.main()
