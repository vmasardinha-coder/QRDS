import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_V1_20260929.json"
class T(unittest.TestCase):
 def test_approved_v1_is_frozen_and_safe(self):
  x=json.loads(P.read_text())
  self.assertEqual(x["status"],"FROZEN_APPROVED_FORWARD_COLLECTION_AUTHORIZED")
  self.assertTrue(x["credit_enabled"])
  self.assertEqual(x["causal_capture"]["minimum_eligible_pairs"],10000)
  self.assertEqual(x["causal_capture"]["minimum_elapsed_calendar_days"],7)
  self.assertEqual(x["causal_capture"]["minimum_distinct_observation_days"],3)
  self.assertEqual(x["decision_to_execution_contract"]["virtual_order_size_grid_percent_of_observed_depth10_side_liquidity"],[1,10,25,50,100])
  self.assertEqual(x["decision_to_execution_contract"]["latency_ms_grid"],[0,50,100,250,500])
  self.assertEqual(x["decision_to_execution_contract"]["fee_stress_bps_grid"],[0,5,10])
  self.assertEqual(x["replay"]["minimum_effective_executions_per_primary_scenario"],1000)
  self.assertFalse(x["pass_fail_contract"]["profitability_is_pass_criterion"])
  s=x["safety"]; self.assertTrue(s["RESEARCH_ONLY"] and s["SHADOW_ONLY"] and s["NO_BACKFILL"] and s["NO_RETUNE"])
  self.assertEqual(s["ORDERS"],0); self.assertEqual(s["REAL_CAPITAL_BRL"],0)
if __name__=="__main__": unittest.main()
