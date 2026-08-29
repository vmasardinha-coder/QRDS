import unittest

from tools.gate_btc_2_system10_event_envelope import build_event_envelope
from tools.gate_btc_2_system10_readiness_record import build_readiness_record, verify_readiness_record


class System10ReadinessRecordTests(unittest.TestCase):
    def test_zero_event_baseline_is_plumbing_only(self):
        envelope = build_event_envelope([])
        record = build_readiness_record(envelope)
        verify_readiness_record(record)
        self.assertEqual(record["event_count"], 0)
        self.assertEqual(record["readiness_scope"], "PLUMBING_ONLY_NO_ENGINE_PROOF")
        self.assertFalse(record["engine_parity_proven"])
        self.assertFalse(record["engine_instantiated"])
        self.assertFalse(record["engine_execution"])
        self.assertFalse(record["nautilus_execution_enabled"])
        self.assertFalse(record["stage_9_complete"])
        self.assertFalse(record["system_10_complete"])
        self.assertFalse(record["prospective_credit_allowed"])
        self.assertFalse(record["economics_allowed"])
        self.assertFalse(record["engine_feed"])
        self.assertEqual(record["orders"], 0)
        self.assertEqual(record["real_capital_brl"], 0)

    def test_tamper_fails_closed(self):
        envelope = build_event_envelope([])
        record = build_readiness_record(envelope)
        record["engine_parity_proven"] = True
        with self.assertRaises(RuntimeError):
            verify_readiness_record(record)


if __name__ == "__main__":
    unittest.main()
