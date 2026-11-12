import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.gate_btc_qmaster_reporting_cache import refresh

class CacheTests(unittest.TestCase):
 def source(self,day='2026-11-11',raw=b'csv'):
  meta=dict(data_as_of=day,status='PASS',operational_status='NOT_APPROVED',orders_generated=0,real_capital_used=0,csv_sha256=hashlib.sha256(raw).hexdigest(),csv_path='GATE_BTC_QMASTER_LATEST.csv')
  return json.dumps(meta).encode(),raw
 def reader(self,meta,raw,calls):
  def read(repo,*args):
   calls.append(args)
   if args[0]=='fetch':return b''
   if args[0]=='rev-parse':return b'abc123\n'
   if args[0]=='show':return meta if args[1].endswith('.txt') else raw
   raise AssertionError('WORKTREE_WRITE_FORBIDDEN:'+str(args))
  return read
 def test_reads_objects_without_checkout_reset_or_merge(self):
  with tempfile.TemporaryDirectory() as td:
   calls=[];m,r=self.source();p,proof=refresh('dirty-detached-repo',Path(td),self.reader(m,r,calls));self.assertEqual(p.read_bytes(),m);self.assertFalse(proof['worktree_changed']);self.assertEqual([c[0] for c in calls],['fetch','rev-parse','show','show'])
 def test_bad_hash_never_updates_cache_pointer(self):
  with tempfile.TemporaryDirectory() as td:
   m,r=self.source()
   with self.assertRaisesRegex(ValueError,'HASH'):refresh('repo',Path(td),self.reader(m,b'tampered',[]))
   self.assertFalse((Path(td)/'CURRENT.json').exists())
 def test_remote_regression_leaves_previous_snapshot(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);m,r=self.source();refresh('repo',root,self.reader(m,r,[]));before=(root/'CURRENT.json').read_bytes();m,r=self.source('2026-11-07')
   with self.assertRaisesRegex(ValueError,'REGRESSION'):refresh('repo',root,self.reader(m,r,[]))
   self.assertEqual((root/'CURRENT.json').read_bytes(),before)
 def test_fetch_failure_is_visible(self):
  with tempfile.TemporaryDirectory() as td:
   def fail(*args):raise RuntimeError('FETCH_FAILED')
   with self.assertRaisesRegex(RuntimeError,'FETCH_FAILED'):refresh('repo',Path(td),fail)
