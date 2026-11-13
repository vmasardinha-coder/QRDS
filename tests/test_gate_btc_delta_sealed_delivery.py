import json,tempfile,unittest
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
from tools import gate_btc_delta_sealed_delivery as recovery
from tools import gate_btc_delta_paper_monitor as monitor

class RecoveryTests(unittest.TestCase):
 def fixture(self,root,days=2):
  c=root/'contract.json';c.write_text('{}');a=root/'archive';a.mkdir();r=root/'runtime';r.mkdir()
  (r/'STATUS.json').write_text(json.dumps(dict(data_as_of='2026-11-07',observed_days=86)))
  monitor.write_csv(r/'DAILY_NAV.csv',[dict(date='2026-11-07',nav='original')],['date','nav'])
  for i in range(days):
   day=(date(2026,11,8)+timedelta(days=i)).isoformat();z=a/(day+'.zip');z.write_bytes(day.encode())
   receipt=dict(date=day,source_manifest_data_as_of=day,canonical_contract_sha256=monitor.h(c.read_bytes()),source_zip_sha256=monitor.h(z.read_bytes()),source_run_id=i+1,source_only=True,paper_nav_appended=False,backfill_performed=False,scientific_credit=0,orders_generated=0,real_capital_used=0,engine_feed=False)
   (a/(day+'.json')).write_text(json.dumps(receipt))
  return c,a,r
 def load(self,c,z):
  day=date.fromisoformat(z.stem);return dict(manifest=dict(data_as_of=day.isoformat(),run_utc=(day+timedelta(days=1)).isoformat()+'T07:00:00+00:00'))
 def process(self,c,z,r,rid):
  st=json.loads((r/'STATUS.json').read_text());st.update(data_as_of=z.stem,observed_days=st['observed_days']+1)
  rows=monitor.read_csv(r/'DAILY_NAV.csv');rows.append(dict(date=z.stem,nav='delivered'));monitor.write_csv(r/'DAILY_NAV.csv',rows,['date','nav']);(r/'STATUS.json').write_text(json.dumps(st))
 def test_exact_sealed_batch_preserves_original_prefix(self):
  with tempfile.TemporaryDirectory() as td:
   c,a,r=self.fixture(Path(td));old=monitor.read_csv(r/'DAILY_NAV.csv')
   with patch.object(monitor,'load',side_effect=self.load),patch.object(monitor,'process',side_effect=self.process):z=recovery.recover(c,a,r,'2026-11-09')
   self.assertEqual(z['observed_days'],88);self.assertEqual(monitor.read_csv(r/'DAILY_NAV.csv')[:len(old)],old);self.assertFalse(z['source_returns_reconstructed'])
 def test_missing_day_never_skips_gap_or_changes_original(self):
  with tempfile.TemporaryDirectory() as td:
   c,a,r=self.fixture(Path(td),1);before=(r/'STATUS.json').read_bytes()
   with patch.object(monitor,'load',side_effect=self.load),self.assertRaisesRegex(ValueError,'SOURCE_MISSING'):recovery.recover(c,a,r,'2026-11-09')
   self.assertEqual((r/'STATUS.json').read_bytes(),before)
 def test_hash_tamper_never_changes_original(self):
  with tempfile.TemporaryDirectory() as td:
   c,a,r=self.fixture(Path(td));(a/'2026-11-08.zip').write_bytes(b'tampered')
   with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):recovery.recover(c,a,r,'2026-11-09')
   self.assertEqual(json.loads((r/'STATUS.json').read_text())['observed_days'],86)
 def test_late_reconstruction_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   c,a,r=self.fixture(Path(td));fake=dict(manifest=dict(data_as_of='2026-11-08',run_utc='2026-11-12T07:00:00+00:00'))
   with patch.object(monitor,'load',return_value=fake),self.assertRaisesRegex(ValueError,'ORIGINAL_DAILY_RUN'):recovery.recover(c,a,r,'2026-11-09')
 def test_engine_failure_leaves_original_untouched(self):
  with tempfile.TemporaryDirectory() as td:
   c,a,r=self.fixture(Path(td));before=(r/'DAILY_NAV.csv').read_bytes()
   with patch.object(monitor,'load',side_effect=self.load),patch.object(monitor,'process',side_effect=RuntimeError('engine')),self.assertRaisesRegex(RuntimeError,'engine'):recovery.recover(c,a,r,'2026-11-09')
   self.assertEqual((r/'DAILY_NAV.csv').read_bytes(),before)
 def test_current_batch_is_noop(self):
  with tempfile.TemporaryDirectory() as td:
   c,a,r=self.fixture(Path(td));self.assertEqual(recovery.recover(c,a,r,'2026-11-07')['status'],'UP_TO_DATE')
