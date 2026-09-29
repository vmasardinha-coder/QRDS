import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "artifacts/gate_btc_2/SYSTEM11_STRUCTURAL_READINESS_20260929.json"

class System11ReadinessTest(unittest.TestCase):
    def test_fail_closed_readiness(self):
        x=json.loads(P.read_text(encoding="utf-8"))
        self.assertEqual(x["system"],11)
        self.assertEqual(x["status"],"STRUCTURAL_READY_WAITING_FROZEN_STRESS_REPLAY_PREREG")
        self.assertFalse(x["system11_complete"])
        self.assertEqual(x["dependency"]["system10_required_status"],"COMPLETE_RESEARCH_PARITY")
        self.assertEqual(x["dependency"]["system10_replay_events"],239)
        self.assertFalse(x["existing_lob_capability_evidence"]["rejected_signal_result_reusable_for_system11_credit"])
        self.assertFalse(x["existing_forward_feature_handoff"]["historical_pit_panel_available"])
        self.assertFalse(x["existing_forward_feature_handoff"]["economic_claim_authorized"])
        self.assertFalse(x["existing_forward_feature_handoff"]["factory_migration_authorized"])
        self.assertIn("PREREGISTER_SYSTEM11_CAUSAL_BOOK_DATASET_CONTRACT",x["unresolved_before_capture_credit"])
        self.assertIn("PREREGISTER_EXECUTION_STRESS_REPLAY_CONTRACT",x["unresolved_before_capture_credit"])
        s=x["safety"]
        self.assertTrue(s["RESEARCH_ONLY"] and s["SHADOW_ONLY"] and s["NO_BACKFILL"] and s["NO_RETUNE"])
        self.assertFalse(s["ENGINE_FEED"])
        self.assertEqual(s["ORDERS"],0)
        self.assertEqual(s["REAL_CAPITAL_BRL"],0)

if __name__ == "__main__":
    unittest.main()
