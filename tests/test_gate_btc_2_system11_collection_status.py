import json,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"tools"))
from gate_btc_2_system11_collection_status import status
P=json.loads((ROOT/"artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_V1_20260929.json").read_text())
class T(unittest.TestCase):
 def test_partial_monitoring_never_claims_conclusion(self):
  rows=[{"eligible_pair":True,"observation_date":"2026-09-29"} for _ in range(100)]
  x=status(P,rows); self.assertEqual(x["eligible_pairs"],100); self.assertFalse(x["dataset_gate_ready"]); self.assertFalse(x["partial_result_is_scientific_conclusion"])
 def test_all_three_dataset_gates_required(self):
  rows=[]
  for d in ["2026-09-29","2026-09-30","2026-10-05"]:
   rows += [{"eligible_pair":True,"observation_date":d} for _ in range(4000)]
  x=status(P,rows); self.assertTrue(x["dataset_gate_ready"]); self.assertGreaterEqual(x["elapsed_calendar_days"],7); self.assertGreaterEqual(x["distinct_observation_days"],3)
if __name__=="__main__": unittest.main()
