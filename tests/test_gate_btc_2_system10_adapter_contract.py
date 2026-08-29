import copy
import unittest

from tools.gate_btc_2_system10_adapter_contract import project_adapter_events, verify_adapter_contract
from tools.gate_btc_2_system10_event_envelope import build_event_envelope


class System10AdapterContractTests(unittest.TestCase):
    def test_empty_reference_contract_is_safe(self):
        envelope = build_event_envelope([])
        contract = project_adapter_events(envelope, "REFERENCE")
        verify_adapter_contract(contract)
        self.assertEqual(contract["event_count"], 0)
        self.assertFalse(contract["engine_execution"])
        self.assertFalse(contract["nautilus_execution_enabled"])
        self.assertFalse(contract["system_10_complete"])
        self.assertEqual(contract["orders"], 0)
        self.assertEqual(contract["real_capital_brl"], 0)

    def test_nautilus_shadow_identity_does_not_enable_engine(self):
        envelope = build_event_envelope([])
        contract = project_adapter_events(envelope, "NAUTILUS_SHADOW_ADAPTER")
        verify_adapter_contract(contract)
        self.assertEqual(contract["adapter_name"], "NAUTILUS_SHADOW_ADAPTER")
        self.assertFalse(contract["engine_execution"])
        self.assertFalse(contract["nautilus_execution_enabled"])

    def test_unauthorized_adapter_fails_closed(self):
        envelope = build_event_envelope([])
        with self.assertRaises(RuntimeError):
            project_adapter_events(envelope, "LIVE_ENGINE")

    def test_tamper_rejected(self):
        envelope = build_event_envelope([])
        contract = project_adapter_events(envelope, "REFERENCE")
        tampered = copy.deepcopy(contract)
        tampered["engine_execution"] = True
        with self.assertRaises(RuntimeError):
            verify_adapter_contract(tampered)


if __name__ == "__main__":
    unittest.main()
