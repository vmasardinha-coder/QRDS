import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLOCK = ROOT / "tools" / "gate_btc_2_stage9_bitget_collection_clock_v1.json"
WORKFLOW = ROOT / ".github" / "workflows" / "gate-btc-2-stage9-bitget-forward-adapter.yml"


class Stage9BitgetCollectionClockTests(unittest.TestCase):
    def test_authorized_hourly_clock_is_fail_closed(self):
        d = json.loads(CLOCK.read_text(encoding="utf-8"))
        self.assertEqual(d["schema"], "gate_btc.2_0.stage9_bitget_collection_clock.v1")
        self.assertEqual(d["stage_id"], 9)
        self.assertEqual((d["provider"], d["venue"], d["instrument"]), ("BITGET_PUBLIC_V2", "BITGET", "BTCUSDT"))
        self.assertTrue(d["authorization"]["human_authorized"])
        self.assertEqual(d["clock"]["cadence_minutes"], 60)
        self.assertEqual(d["clock"]["cron_utc"], "0 * * * *")
        self.assertFalse(d["clock"]["missed_runs_backfilled"])
        self.assertTrue(d["clock"]["first_scheduled_capture_must_postdate_clock_merge"])
        self.assertFalse(d["scientific_boundary"]["required_n_changed"])
        self.assertFalse(d["scientific_boundary"]["statistical_independence_claimed"])
        self.assertFalse(d["scientific_boundary"]["qualification_or_prior_capture_receives_new_credit"])
        s = d["safety"]
        self.assertTrue(s["research_only"] and s["shadow_only"] and s["not_approved"])
        self.assertFalse(s["engine_feed"])
        self.assertEqual(s["orders_generated"], 0)
        self.assertEqual(s["real_capital_brl"], 0)
        self.assertTrue(s["no_retune"] and s["no_backfill"] and s["fail_closed"])
        self.assertFalse(s["promotion_allowed"] or s["economics_allowed"] or s["stage_9_complete"])

    def test_workflow_schedule_matches_preregistered_clock(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "0 * * * *"', workflow)
        self.assertIn('GATE_BTC_STAGE9_CAPTURE_CADENCE_MINUTES: "60"', workflow)
        self.assertIn('gate_btc_2_stage9_bitget_collection_clock_v1.json', workflow)


if __name__ == "__main__":
    unittest.main()
