import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from tools import gate_btc_momentum_m3_gap_epoch as gap
from tools import gate_btc_momentum_m3_economics as econ

class PreservedGapTests(unittest.TestCase):
    def price_fixture(self,base):
        root=base/'momentum_m3_economics';root.mkdir()
        econ.save(root/'LEDGER.json',{'state':{'last_cutoff':'2026-11-02','return_observations':20,'nav':0.72}})
        econ.save(root/'ACTIVATION.json',{'first_eligible_cutoff':'2026-10-13'})
        econ.save(root/'CONTRACT.json',econ.read(econ.CONTRACT))
        econ.save(root/'STATUS.json',{'status':'FAILED_M3_ECONOMIC_DELIVERY','error':'MISSING_REQUIRED_PRICES: LEO','updated_at_utc':'2026-11-04T11:00:00+00:00'})
        src=base/'momentum_m1_m2';src.mkdir()
        for day in gap.required('2026-11-04'):(src/(day+'.json')).write_text('{}')
        return root

    def test_price_gap_preserves_bytes_and_arms_only_future_without_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=self.price_fixture(base)
            before={p.name:p.read_bytes() for p in root.glob('*.json')}
            at=datetime(2026,11,5,12,tzinfo=timezone.utc)
            with patch.object(econ,'validate'):
                result=gap.prepare(base,'2026-11-04',at)
                second=gap.prepare(base,'2026-11-04',at)
            self.assertFalse(result['can_compute']);self.assertTrue(result['price_gap'])
            self.assertEqual(second['status'],'WAIT_FIRST_FUTURE_EPOCH_CUTOFF')
            for name in ['LEDGER.json','ACTIVATION.json','CONTRACT.json']:
                self.assertEqual((root/name).read_bytes(),before[name])
            epoch=Path(result['economic_dir'])
            self.assertEqual(econ.read(epoch/'ACTIVATION.json')['first_eligible_cutoff'],'2026-11-06')
            self.assertFalse((epoch/'LEDGER.json').exists())
            self.assertEqual(econ.read(root/'gaps/2026-11-04.json')['missing_economic_cutoffs'],['2026-11-03','2026-11-04'])
            self.assertEqual(econ.read(root/'STATUS.json')['return_observations'],20)

    def test_price_gap_rejects_late_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=self.price_fixture(base)
            with self.assertRaisesRegex(ValueError,'CURRENT_PROSPECTIVE'):
                gap.prepare(base,'2026-11-04',datetime(2026,11,6,12,tzinfo=timezone.utc))
            self.assertFalse((root/'gaps').exists())

    def test_unrelated_failure_does_not_start_epoch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=self.price_fixture(base)
            status=econ.read(root/'STATUS.json');status['error']='HASH_MISMATCH';econ.save(root/'STATUS.json',status)
            self.assertIsNone(gap.preserve_price_gap(base,'2026-11-04',datetime(2026,11,5,12,tzinfo=timezone.utc),[]))
            self.assertFalse((root/'gaps').exists())

    def test_summary_preserves_multiple_epochs_without_combining_nav(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);root=self.price_fixture(base)
            prior=root/'epochs/after_gap_2026-10-12'
            econ.save(prior/'LEDGER.json',{'state':{'return_observations':4,'nav':0.8}})
            result=gap.summarize(base,root/'epochs/after_gap_2026-11-04')
            self.assertEqual(result['legacy_return_observations'],24)
            self.assertIsNone(result['nav']);self.assertIsNone(result['legacy_nav'])
            self.assertFalse(result['economic_series_comparable_across_gap'])

    def test_gap_is_zero_credit_idempotent_and_next_day_uses_new_epoch(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            src=base/'momentum_m1_m2'
            src.mkdir()
            for day in ('2026-10-05','2026-09-21','2026-10-06','2026-09-29','2026-09-22'):
                (src/(day+'.json')).write_text('{}')
            root=base/'momentum_m3_economics'
            root.mkdir()
            econ.save(root/'LEDGER.json',{'state':{'last_cutoff':'2026-10-04',
                'return_observations':5,'nav':1.0048975475}})
            econ.save(root/'ACTIVATION.json',{'first_eligible_cutoff':'2026-09-28'})
            econ.save(root/'CONTRACT.json',econ.read(econ.CONTRACT))
            econ.save(root/'STATUS.json',{'status':'FAILED_M3_ECONOMIC_DELIVERY'})
            at=datetime(2026,10,6,12,tzinfo=timezone.utc)
            with patch.object(econ,'validate'):
                first=gap.prepare(base,'2026-10-05',at)
                again=gap.prepare(base,'2026-10-05',at)
            self.assertFalse(first['can_compute'])
            self.assertEqual(first['missing_source_cutoffs'],['2026-09-28'])
            self.assertEqual(first['economic_dir'],again['economic_dir'])
            self.assertEqual(econ.read(root/'gaps/2026-10-05.json')['economic_credit'],0)
            self.assertEqual(econ.read(root/'STATUS.json')['return_observations'],5)
            self.assertEqual(econ.read(root/'preserved/STATUS_before_gap.json')['status'],
                             'FAILED_M3_ECONOMIC_DELIVERY')
            forward=gap.prepare(base,'2026-10-06',datetime(2026,10,7,12,tzinfo=timezone.utc))
            self.assertTrue(forward['can_compute'])
            self.assertEqual(forward['economic_dir'],first['economic_dir'])
            self.assertEqual(econ.read(Path(forward['economic_dir'])/'ACTIVATION.json')['first_eligible_cutoff'],
                             '2026-10-06')
            self.assertFalse((src/'2026-09-28.json').exists())

if __name__=='__main__':unittest.main()

