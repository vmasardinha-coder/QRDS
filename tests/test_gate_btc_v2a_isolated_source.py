import hashlib,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
from tools.gate_btc_v2a_isolated_source import validate

class IsolatedV2ATests(unittest.TestCase):
 def test_current_binding_and_fail_closed_boundaries(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d); hashes={}
   names=['data/processed/qos_v2a_master_daily.csv','data/raw/coingecko_current_universe_v04.csv','outputs/download_failures_v2a.csv','outputs/source_attempts_v2a.json']
   for n in names:
    p=r/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'evidence');hashes[n]=hashlib.sha256(b'evidence').hexdigest()
   m=dict(technical_status='PASS',data_quality_status='PASS',operational_status='NOT_APPROVED',real_orders=0,capital_used=0,evidence_status='RESEARCH_ONLY_NOT_PROMOTED',data_as_of='2026-11-11',run_utc='2026-11-12T07:00:00+00:00',input_files_sha256=hashes,source_trace_sha256=hashes[names[-1]])
   p=r/'outputs/v2a_run_manifest.json';now=datetime(2026,11,12,tzinfo=timezone.utc)
   def write():p.write_text(json.dumps(m))
   write();self.assertEqual(validate(r,now),'2026-11-11')
   for key,value in [('data_as_of','2026-11-10'),('run_utc','2026-11-11T07:00:00+00:00'),('real_orders',1),('capital_used',1),('technical_status','FAIL'),('evidence_status','PROMOTED')]:
    old=m[key];m[key]=value;write()
    with self.subTest(key=key),self.assertRaises(ValueError):validate(r,now)
    m[key]=old
   write()
   for n in names:
    (r/n).write_bytes(b'tampered')
    with self.subTest(path=n),self.assertRaises(ValueError):validate(r,now)
    (r/n).write_bytes(b'evidence')
