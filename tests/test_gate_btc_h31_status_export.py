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


    def test_trigger_count_does_not_become_closed_return_count(self):
        paper={"H31_SHADOW_SIMULATED_TRADES":7,"H31_SHADOW_CLOSED_TRADES":6,"ORDERS":0,"REAL_CAPITAL":0}
        out=build({"orders":0,"real_capital":0},paper)
        self.assertEqual(out["simulated_trades"],7)
        self.assertEqual(out["closed_trades"],6)
        self.assertEqual(paper["H31_SHADOW_CLOSED_TRADES"],6)

    def test_missing_close_count_remains_unknown(self):
        out=build({"orders":0,"real_capital":0},{"H31_SHADOW_SIMULATED_TRADES":7})
        self.assertIsNone(out["closed_trades"])


    def test_explicit_intraday_counters_override_stale_paper_without_changing_economics(self):
        paper={"H31_SHADOW_SESSIONS":0,"H31_SHADOW_SIMULATED_TRADES":0,"cumulative_gross_bps":12.}
        live={"H31_SHADOW_SESSIONS":26,"H31_SHADOW_SIMULATED_TRADES":7,"H31_SHADOW_CLOSED_TRADES":6,"H31_MT5_READY":True}
        out=build({"eligible_observations":0,"partial_prospective_economics_exposed":False},paper,live)
        self.assertEqual((out["shadow_sessions"],out["simulated_trades"],out["closed_trades"]),(26,7,6))
        self.assertEqual(out["economics"]["gross_bps"],12.)
        self.assertEqual(out["eligible_observations"],0)
        self.assertEqual(out["shadow_counter_source"],"INTRADAY_STATUS")
        self.assertTrue(out["paper_bridge"]["mt5_ready"])
        self.assertEqual(paper["H31_SHADOW_SESSIONS"],0)

    def test_unsafe_intraday_input_is_rejected(self):
        with self.assertRaises(ValueError):
            build({}, {}, {"ORDERS":1})


if __name__ == "__main__":
    unittest.main()
