import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gate_btc_2_system12_readiness import assess


class T(unittest.TestCase):
    def test_missing_or_partial_upstream_cannot_complete_system12(self):
        for report in (None, {"status": "INCONCLUSIVE_ABSTAIN", "system11_complete": False}):
            x = assess(report, None)
            self.assertFalse(x["upstream_system11_ready"])
            self.assertFalse(x["system12_complete"])
            self.assertFalse(x["system13_dependency_released"])
            self.assertEqual(x["scientific_credit"], 0)
            self.assertEqual(x["orders"], 0)

    def test_complete_boolean_without_hash_bound_evidence_is_blocked(self):
        report = {"status": "PASS_FROZEN_LOB_STRESS_REPLAY", "system11_complete": True}
        self.assertEqual(assess(report, None)["status"], "BLOCKED_MISSING_HASH_BOUND_SYSTEM11_LEDGER")
        self.assertEqual(assess(report, [])["status"], "BLOCKED_INVALID_SYSTEM11_EVIDENCE")
        self.assertFalse(assess(report, [])["system12_complete"])


if __name__ == "__main__":
    unittest.main()
