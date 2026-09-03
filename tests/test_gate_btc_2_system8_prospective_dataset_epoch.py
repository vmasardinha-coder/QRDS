import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
EPOCH = ROOT / "tools" / "gate_btc_2_system8_prospective_dataset_epoch_v1.json"

class System8ProspectiveDatasetEpochTests(unittest.TestCase):
    def test_authorized_epoch_is_zero_credit_and_fail_closed(self):
        d = json.loads(EPOCH.read_text(encoding="utf-8"))
        self.assertEqual(d["schema"], "gate_btc.2_0.system8_prospective_dataset_epoch.v1")
        self.assertEqual(d["system_id"], 8)
        self.assertTrue(d["authorization"]["human_authorized"])
        self.assertEqual(d["predecessor"]["original_historical_dataset_seal"], "UNSEALED_FAILED")
        self.assertEqual(d["predecessor"]["historical_credit_into_this_epoch"], 0)
        self.assertEqual(d["predecessor"]["counter_carryover"], 0)
        self.assertTrue(d["predecessor"]["negative_evidence_preserved"])
        self.assertEqual(d["cutover"]["pre_merge_observations_credit"], 0)
        self.assertFalse(d["cutover"]["backdating_allowed"])
        self.assertFalse(d["cutover"]["missed_observations_backfilled"])
        self.assertFalse(d["cutover"]["timestamp_repair_allowed"])
        self.assertTrue(d["methodology"]["point_in_time_required"])
        self.assertFalse(d["methodology"]["survivorship_bias_allowed"])
        self.assertFalse(d["methodology"]["silent_source_substitution"])
        self.assertTrue(d["methodology"]["independent_readiness_clock"])
        self.assertEqual(d["readiness"]["initial_state"], "COLLECT_MORE")
        self.assertEqual(d["readiness"]["initial_counter"], 0)
        self.assertFalse(d["readiness"]["economics_allowed"])
        self.assertFalse(d["readiness"]["automatic_promotion"])
        self.assertTrue(d["separation"]["stage9_clock_unchanged"])
        self.assertTrue(d["separation"]["system15_independent"])
        s=d["safety"]
        self.assertTrue(s["RESEARCH_ONLY"] and s["SHADOW_ONLY"] and s["NOT_APPROVED"])
        self.assertFalse(s["ENGINE_FEED"])
        self.assertEqual(s["ORDERS"], 0)
        self.assertEqual(s["REAL_CAPITAL_BRL"], 0)
        self.assertTrue(s["NO_RETUNE"] and s["NO_BACKFILL"] and s["NO_COUNTER_RESET"] and s["NO_SILENT_SOURCE_SUBSTITUTION"] and s["FAIL_CLOSED"])

if __name__ == "__main__":
    unittest.main()
