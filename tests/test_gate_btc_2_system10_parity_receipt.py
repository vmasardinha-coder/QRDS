import copy
import unittest

from tools.gate_btc_2_system10_event_envelope import build_event_envelope
from tools.gate_btc_2_system10_parity_receipt import build_parity_receipt, verify_parity_receipt


class System10ParityReceiptTests(unittest.TestCase):
    def test_empty_baseline_is_zero_event_and_safe(self):
        envelope = build_event_envelope([])
        receipt = build_parity_receipt(envelope, "REFERENCE", [])
        verify_parity_receipt(receipt)
        self.assertEqual(receipt["event_count"], 0)
        self.assertTrue(receipt["parity_pass"])
        self.assertFalse(receipt["nautilus_execution_enabled"])
        self.assertFalse(receipt["system_10_complete"])
        self.assertEqual(receipt["orders"], 0)
        self.assertEqual(receipt["real_capital_brl"], 0)

    def test_unauthorized_adapter_fails_closed(self):
        envelope = build_event_envelope([])
        with self.assertRaises(RuntimeError):
            build_parity_receipt(envelope, "LIVE_ENGINE", [])

    def test_receipt_tamper_fails(self):
        envelope = build_event_envelope([])
        receipt = build_parity_receipt(envelope, "NAUTILUS_SHADOW_ADAPTER", [])
        tampered = copy.deepcopy(receipt)
        tampered["orders"] = 1
        with self.assertRaises(RuntimeError):
            verify_parity_receipt(tampered)


if __name__ == "__main__":
    unittest.main()
