import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.gate_btc_2_item3d_forward_adjudicator import load_verified_records

class IntegrityTests(unittest.TestCase):
 def good(self):
  return dict(schema='gate_btc_2.factory_item3c_forward_session.v1',session='2026-11-11',historical_credit=0,retroactive_credit=0,survivor_credit=0,orders=0,real_capital=0,engine_feed=False,promotion_authority=False,no_backfill=True,no_retune=True,active_family_count=1,family_observations=[dict(family_id='H1',state='TRIGGER',outcomes=[dict(horizon_minutes=30)])])
 def seal(self,root,d):
  d=dict(d);d['record_sha256']=hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();p=root/'2026-11-11.json';p.write_text(json.dumps(d));return p
 def test_accepts_valid_sealed_record(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);self.seal(r,self.good());self.assertEqual(len(load_verified_records(r)),1)
 def test_rejects_tampered_record(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);p=self.seal(r,self.good());d=json.loads(p.read_text());d['active_family_count']=2;p.write_text(json.dumps(d))
   with self.assertRaisesRegex(RuntimeError,'HASH_MISMATCH'):load_verified_records(r)
 def test_rejects_unsafe_sealed_record(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);d=self.good();d['orders']=1;self.seal(r,d)
   with self.assertRaisesRegex(RuntimeError,'AUTHORITY'):load_verified_records(r)
 def test_rejects_duplicate_family(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);d=self.good();d['family_observations']*=2;d['active_family_count']=2;self.seal(r,d)
   with self.assertRaisesRegex(RuntimeError,'POPULATION'):load_verified_records(r)
 def test_rejects_duplicate_horizon(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);d=self.good();d['family_observations'][0]['outcomes']*=2;self.seal(r,d)
   with self.assertRaisesRegex(RuntimeError,'DUPLICATE_HORIZON'):load_verified_records(r)
 def test_rejects_date_filename_mismatch(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);d=self.good();d['session']='2026-11-10';self.seal(r,d)
   with self.assertRaisesRegex(RuntimeError,'IDENTITY'):load_verified_records(r)
