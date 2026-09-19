import unittest
from tools.gate_btc_h31_status_export import build


class H31StatusExportTest(unittest.TestCase):
    def test_reporting_projection_preserves_zero_authority(self):
        prospective = {
            "status": "ACTIVE_PROSPECTIVE",
            "clock_started": True,
            "eligible_observations": 0,
            "latest_date": None,
            "freeze_rule_hash_sha256": "a" * 64,
            "partial_prospective_economics_exposed": False,
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
        }
        paper = {
            "H31_SHADOW_PAPER_STATUS": "ACTIVE",
            "H31_SHADOW_SESSIONS": 9,
            "H31_SHADOW_SIMULATED_TRADES": 1,
            "H31_MT5_READY": True,
            "H31_MT5_PARITY_OBSERVATIONS": 9,
            "SHADOW_CREDIT_TO_CANONICAL": 0,
            "NO_BACKFILL": True,
            "NO_RETUNE": True,
            "ORDERS": 0,
            "REAL_CAPITAL": 0,
            "metrics_sample_status": "NOT_ENOUGH_OBSERVATIONS",
        }
        out = build(prospective, paper)
        self.assertTrue(out["reporting_only"])
        self.assertFalse(out["scientific_authority"])
        self.assertEqual(out["eligible_observations"], 0)
        self.assertEqual(out["shadow_sessions"], 9)
        self.assertEqual(out["simulated_trades"], 1)
        self.assertTrue(out["economics_locked"])
        self.assertEqual(out["orders"], 0)
        self.assertEqual(out["real_capital"], 0)
        self.assertEqual(out["shadow_credit_to_canonical"], 0)

    def test_unsafe_state_fails_closed(self):
        with self.assertRaises(ValueError):
            build({"orders": 1, "real_capital": 0}, {"ORDERS": 0, "REAL_CAPITAL": 0})


if __name__ == "__main__":
    unittest.main()
