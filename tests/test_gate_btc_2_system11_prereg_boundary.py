import json,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from gate_btc_2_system11_prereg_boundary import assess
P=ROOT/"artifacts/gate_btc_2/SYSTEM11_LOB_STRESS_PREREG_BOUNDARY_20260929.json"

class T(unittest.TestCase):
    def test_boundary_is_complete_but_credit_fail_closed(self):
        x=json.loads(P.read_text(encoding="utf-8"))
        r=assess(x)
        self.assertTrue(r["required_field_names_declared"])
        self.assertTrue(r["safety_pass"])
        self.assertFalse(r["credit_enabled"])
        self.assertEqual(r["status"],"BLOCKED_PENDING_EXPLICIT_SYSTEM11_PARAMETERS")
        self.assertFalse(r["system11_complete"])
        self.assertFalse(x["existing_evidence_policy"]["existing_rows_receive_system11_credit"])
        self.assertEqual(x["existing_evidence_policy"]["historical_rows_backfilled"],0)
        g=x["existing_execution_realism_gate"]
        self.assertEqual(g["gate_id"],"AUDIT-XEXEC-01")
        self.assertEqual(g["status"],"REGISTERED_VALIDATION_GATE")
        self.assertTrue(g["fail_closed_on_missing_execution_semantics"])
        self.assertFalse(g["external_numeric_thresholds_imported"])
        self.assertTrue(g["separate_scientific_decision_for_stress_envelope"])
        self.assertIn("decision_to_execution_contract",x["required_new_preregistration_fields"]["execution_stress_replay"])

if __name__=="__main__":
    unittest.main()
