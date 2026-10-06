import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tools import gate_btc_prl_alt_next_epoch as next_epoch

class NextEpochTests(unittest.TestCase):
    def test_old_epoch_is_intact_and_next_month_is_separate(self):
        for lane in ('prl50','alt'):
            with self.subTest(lane=lane),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                old=root/'epochs/monthly_20260930'
                (old/'snapshots').mkdir(parents=True)
                (old/'ANCHOR.json').write_text('{}')
                prior=old/'snapshots/2026-10-04.json'
                prior.write_text('{}')
                bytes_before=prior.read_bytes()
                wait=next_epoch.plan(root,lane,datetime(2026,10,7,12,tzinfo=timezone.utc))
                self.assertEqual(wait['status'],'WAITING_NEXT_APPROVED_MONTH_END')
                self.assertFalse(wait['can_append'])
                self.assertEqual(wait['interrupted_epoch_snapshot_count'],1)
                self.assertEqual(prior.read_bytes(),bytes_before)
                self.assertEqual(next_epoch.plan(root,lane,datetime(2026,10,7,12,tzinfo=timezone.utc))['status'],
                                 'WAITING_NEXT_APPROVED_MONTH_END')
                ready=next_epoch.plan(root,lane,datetime(2026,11,1,12,tzinfo=timezone.utc))
                self.assertEqual(ready['status'],'NEEDS_CURRENT_SOURCE')
                self.assertEqual(ready['next_required_cutoff'],'2026-10-31')
                self.assertEqual(ready['current_epoch_snapshot_count'],0)
                self.assertEqual(prior.read_bytes(),bytes_before)
                self.assertTrue((root/'epochs/monthly_20261031/ANCHOR.json').exists())
                self.assertEqual(next_epoch.config(lane)[2].load_json(old/'PRESERVED_GAP.json')['economic_credit'],0)

if __name__=='__main__':unittest.main()
