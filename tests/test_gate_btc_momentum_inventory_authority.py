import json,tempfile,unittest
from pathlib import Path
from tools.gate_btc_reporting_inventory import complete_inventory
from tools.gate_btc_reporting_authority import m3_status_path
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

    def m3_fixture(self, root, active=True):
        ledger=root/'ledgers/momentum_m3_economics'
        ledger.mkdir(parents=True)
        (ledger/'STATUS.json').write_text(json.dumps({
            'schema':'gate_btc.momentum_m3_economics_status.v2',
            'active_epoch':'epochs/after_gap_2026-10-05',
            'status':'FAILED_M3_ECONOMIC_DELIVERY',
            'return_observations':10, 'net_return':None}))
        if active:
            epoch=ledger/'epochs/after_gap_2026-10-05'
            epoch.mkdir(parents=True)
            (epoch/'STATUS.json').write_text(json.dumps({
                'schema':'gate_btc.momentum_m3_economics_status.v1',
                'status':'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY',
                'data_as_of':'2026-10-11','return_observations':5,
                'cost_status':'N_D','net_return':None,
                'engine_feed':False,'promotion_allowed':False}))
        return ledger, {'components':{},'status':'BLOCKED_INCOMPLETE_DELIVERY',
                        'delivery_complete':False,'warnings':{'stale_components':['b3_h1']},
                        'ledger_inventory':{'momentum_m3_economics':{
                            'status':'FAILED_M3_ECONOMIC_DELIVERY'}}}

    def test_m3_active_epoch_refreshes_cached_failure_without_summing_epochs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); ledger,state=self.m3_fixture(root)
            before={p:p.read_bytes() for p in root.rglob('*.json')}
            out=complete_inventory(root,state)
            row=out['ledger_reporting_summary']['momentum_m3_economics']
            self.assertEqual(row['status'],'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY')
            self.assertEqual(row['return_observations'],5)
            self.assertEqual(row['data_as_of'],'2026-10-11')
            self.assertEqual(row['cost_status'],'N_D')
            self.assertIsNone(row['net_return'])
            self.assertIn('epochs/after_gap_2026-10-05',row['source'])
            self.assertFalse(row['health_authority'])
            self.assertFalse(out['delivery_complete'])
            self.assertEqual(out['status'],'BLOCKED_INCOMPLETE_DELIVERY')
            self.assertEqual(out['warnings']['stale_components'],['b3_h1'])
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*.json')})

    def test_m3_missing_selected_epoch_never_uses_legacy_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); _,state=self.m3_fixture(root,False)
            row=complete_inventory(root,state)['ledger_reporting_summary']['momentum_m3_economics']
            self.assertEqual(row['status'],'NO_CANONICAL_STATUS_FIELD')
            self.assertNotIn('return_observations',row)
            self.assertIsNone(row['sha256'])

    def test_m3_epoch_path_rejects_traversal_or_invalid_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger,_=self.m3_fixture(root)
            for relative in ('../other','/tmp/other','epochs/../other','epochs/',None):
                (ledger/'STATUS.json').write_text(json.dumps({'active_epoch':relative}))
                with self.assertRaises(ValueError):
                    m3_status_path(ledger)

    def test_m3_selected_epoch_cannot_escape_via_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ledger,_=self.m3_fixture(root,False)
            outside=root/'outside';outside.mkdir()
            (ledger/'epochs').mkdir()
            (ledger/'epochs/after_gap_2026-10-05').symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):
                m3_status_path(ledger)

    def test_m3_without_epoch_preserves_existing_root_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=Path(tmp)
            (ledger/'STATUS.json').write_text(json.dumps({'status':'PRESERVED_LEGACY'}))
            self.assertEqual(m3_status_path(ledger),ledger/'STATUS.json')
if __name__=="__main__":unittest.main()

