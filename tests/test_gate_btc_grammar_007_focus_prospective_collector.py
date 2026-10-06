import json
import unittest
from pathlib import Path
class FocusProspectiveContractTest(unittest.TestCase):
 def test_focus_prereg_is_future_only_and_zero_credit(self):
  p=json.loads(Path("artifacts/gate_btc_2/GRAMMAR_007_FOCUS_PROSPECTIVE_PREREG_20261006.json").read_text())
  self.assertEqual(p["family_id"],"XAGRAMMAR_728DC88D691B")
  self.assertEqual(p["activation_utc"],"2026-10-06T00:00:00Z")
  self.assertEqual(p["scientific_credit"],0); self.assertEqual(p["prospective_credit"],0)
  self.assertFalse(p["promotion_authority"]); self.assertTrue(p["safety"]["NO_BACKFILL"])
if __name__=="__main__": unittest.main()
