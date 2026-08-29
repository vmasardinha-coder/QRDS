import copy
import unittest

from tools.gate_btc_2_system10_event_envelope import build_event_envelope
from tools.gate_btc_2_system10_shadow_adapter_fixture import run_shadow_adapter_fixture


class System10ShadowAdapterFixtureTests(unittest.TestCase):
    def test_empty_ledger_path_is_safe_and_deterministic(self):
        envelope = build_event_envelope([])
        first = run_shadow_adapter_fixture(envelope)
        second = run_shadow_adapter_fixture(copy.deepcopy(envelope))
        self.assertEqual(first, second)
        self.assertEqual(first["status"], "PASS_READ_ONLY_PARITY_FIXTURE")
        self.assertEqual(first["event_count"], 0)
        self.assertFalse(first["engine_instantiated"])
        self.assertFalse(first["engine_execution"])
        self.assertFalse(first["nautilus_execution_enabled"])
        self.assertFalse(first["stage_9_complete"])
        self.assertFalse(first["system_10_complete"])
        self.assertFalse(first["economics_allowed"])
        self.assertFalse(first["engine_feed"])
        self.assertEqual(first["orders"], 0)
        self.assertEqual(first["real_capital_brl"], 0)

    def test_tampered_envelope_fails_closed(self):
        envelope = build_event_envelope([])
        envelope["orders"] = 1
        with self.assertRaises(RuntimeError):
            run_shadow_adapter_fixture(envelope)


if __name__ == "__main__":
    unittest.main()
