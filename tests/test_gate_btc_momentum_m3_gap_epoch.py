import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from tools import gate_btc_momentum_m3_gap_epoch as gap
from tools import gate_btc_momentum_m3_economics as econ

class PreservedGapTests(unittest.TestCase):
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
