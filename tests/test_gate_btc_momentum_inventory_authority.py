import json,tempfile,unittest
from pathlib import Path
from tools.gate_btc_reporting_inventory import complete_inventory
class MomentumInventoryAuthorityTests(unittest.TestCase):
    def fixture(self,root,active=True):
        ledger=root/"ledgers/momentum_m1_m2_economics"
        ledger.mkdir(parents=True)
        (ledger/"ECONOMICS_STATUS.json").write_text(json.dumps({"status":"LEGACY","data_as_of":"2026-09-13"}))
        (ledger/"ACTIVE_EPOCH.json").write_text(json.dumps({"relative_path":"epochs/hold_20260928"}))
        if active:
            epoch=ledger/"epochs/hold_20260928";epoch.mkdir(parents=True)
            (epoch/"ECONOMICS_STATUS.json").write_text(json.dumps({"status":"ECONOMICS_ACTIVE_HOLD_GROSS_ONLY","data_as_of":"2026-10-10"}))
        return {"components":{},"status":"BLOCKED_INCOMPLETE_DELIVERY","delivery_complete":False,"ledger_inventory":{"momentum_m1_m2_economics":{"status":"LEGACY","data_as_of":"2026-09-13"}}}
    def test_active_epoch_overrides_preexisting_legacy_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=self.fixture(root)
            result=complete_inventory(root,state)
            row=result["ledger_inventory"]["momentum_m1_m2_economics"]
            self.assertEqual(row["data_as_of"],"2026-10-10")
            self.assertEqual(row["status"],"ECONOMICS_ACTIVE_HOLD_GROSS_ONLY")
            self.assertIn("epochs/hold_20260928",row["source"])
            self.assertEqual(result["status"],"BLOCKED_INCOMPLETE_DELIVERY")
            self.assertFalse(result["delivery_complete"])
            self.assertFalse(row["health_authority"])
    def test_missing_active_evidence_never_falls_back_to_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);state=self.fixture(root,False)
            row=complete_inventory(root,state)["ledger_inventory"]["momentum_m1_m2_economics"]
            self.assertEqual(row["status"],"NO_CANONICAL_STATUS_FIELD")
            self.assertIsNone(row["sha256"])
            self.assertNotIn("data_as_of",row)
            self.assertIn("epochs/hold_20260928",row["source"])
if __name__=="__main__":unittest.main()
