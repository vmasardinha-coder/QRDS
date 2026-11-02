import copy,json,tempfile,unittest,sys,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from gate_btc_factory import prospective_local_operations as op

def record(pid,stamp=10_000_000,signal=.1):
 d={'schema':'gate_btc_2.xagent_signal_observation.v1','producer_id':pid,
    'available_after_ms':stamp,'close_time_ms':stamp,'capture_time_ms':stamp,
    'signal':signal,'economic_outcomes_read':False,'engine_feed':False,'orders':0,'real_capital':0}
 d['record_sha256']=op.sha(json.dumps(d,sort_keys=True,separators=(',',':')).encode());return d
def genesis():
 d={'schema':'gate_btc_2.xagent_breadth_genesis.v1','producer_id':'S-XBREADTH-01',
    'created_at_capture_ms':1,'immutable':True,'historical_reconstruction':False,
    'new_listings_enter':False,'missing_or_delisted_members_replaced':False,
    'member_count':50,'members':['C%03d-USDT'%i for i in range(50)]}
 d['genesis_sha256']=op.breadth.stable_hash(d);return d

class SourceDeliveryTests(unittest.TestCase):
 def test_spot_age_covers_full_frozen_window_with_hour_boundary_refresh(self):
  from datetime import datetime,timezone
  from gate_btc_xagent_spot_experiment import CONTRACT,CONTRACT_SHA256
  from gate_btc_factory.frozen_source_bytes import read_frozen_bytes
  c=json.loads(read_frozen_bytes(CONTRACT,CONTRACT_SHA256));end=datetime.fromisoformat('2026-11-02T'+c['decision_window_utc'][1]+'+00:00')
  old_close=int(datetime(2026,11,2,1,tzinfo=timezone.utc).timestamp()*1000)-1
  refreshed_close=int(datetime(2026,11,2,2,tzinfo=timezone.utc).timestamp()*1000)-1
  with self.assertRaisesRegex(ValueError,'STALE'):op.check_producer(record('S-XSPOT-FLOW-01',stamp=old_close),int(end.timestamp()*1000))
  op.check_producer(record('S-XSPOT-FLOW-01',stamp=refreshed_close),int(end.timestamp()*1000))
  self.assertEqual(c['input_max_age_seconds'],5400)
  installer=(Path(__file__).resolve().parents[1]/'tools/gate_btc_factory_source_delivery_install.ps1').read_text()
  self.assertIn('@{h=2;m=0}',installer)
 def test_stale_future_tampered_or_unsafe_never_publish(self):
  d=record('S-XSPOT-FLOW-01');op.check_producer(d,15_400_000)
  for now in [9_999_999,15_400_001]:
   with self.assertRaisesRegex(ValueError,'STALE_OR_FUTURE'):op.check_producer(d,now)
  bad=copy.deepcopy(d);bad['signal']=.5
  with self.assertRaisesRegex(ValueError,'SEAL'):op.check_producer(bad,10_000_001)
  for change in [{'orders':1},{'economic_outcomes_read':True},{'signal':2}]:
   bad=record('S-XSPOT-FLOW-01');bad.update(change);bad.pop('record_sha256');bad['record_sha256']=op.sha(json.dumps(bad,sort_keys=True,separators=(',',':')).encode())
   with self.assertRaises(ValueError):op.check_producer(bad,10_000_001)

 def test_all_producers_checked_before_any_write_and_genesis_required(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);g=genesis();op.write(root/op.PRODUCER_ROOT/'S-XBREADTH-01/GENESIS.json',g)
   packet={'genesis':g,'records':[record(p) for p in ['S-XSPOT-FLOW-01','S-XTERM-CARRY-01','S-XBREADTH-01']]}
   with patch.object(op.breadth,'validate_genesis',side_effect=lambda x:x):
    packet['records'][-1]=record('S-XBREADTH-01',stamp=1)
    with self.assertRaises(ValueError):op.apply_producers(root,packet,10_000_001)
    self.assertEqual(len(list(root.rglob('*.json'))),1)
    packet['records'][-1]=record('S-XBREADTH-01',signal=None)
    paths=op.apply_producers(root,packet,10_000_001)
    self.assertTrue(all(x.startswith(op.PRODUCER_ROOT+'/') for x in paths))
    d=json.loads((root/op.PRODUCER_ROOT/'S-XBREADTH-01/LATEST.json').read_bytes())
    self.assertIsNone(d['signal'])
    before={str(p):p.read_bytes() for p in root.rglob('*.json')};op.apply_producers(root,packet,10_000_001)
    self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*.json')})
    g['genesis_sha256']='0'*64
    with self.assertRaisesRegex(ValueError,'GENESIS'):op.apply_producers(root,packet,10_000_001)

 def test_later_latest_never_moves_backwards(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);g=genesis();op.write(root/op.PRODUCER_ROOT/'S-XBREADTH-01/GENESIS.json',g)
   ds=[record(p) for p in ['S-XSPOT-FLOW-01','S-XTERM-CARRY-01','S-XBREADTH-01']]
   for d in ds:op.write(root/op.PRODUCER_ROOT/d['producer_id']/'LATEST.json',record(d['producer_id'],stamp=11_000_000))
   with patch.object(op.breadth,'validate_genesis',side_effect=lambda x:x):op.apply_producers(root,{'genesis':g,'records':ds},11_000_001)
   for d in ds:self.assertEqual(json.loads((root/op.PRODUCER_ROOT/d['producer_id']/'LATEST.json').read_bytes())['available_after_ms'],11_000_000)

 def test_basis_wait_missed_are_never_published(self):
  with tempfile.TemporaryDirectory() as tmp:
   for status in ['WAITING_FUTURE_DECISION_WINDOW','MISSED_PREDECISION_WINDOW_ZERO_CREDIT']:
    self.assertEqual(op.apply_basis(Path(tmp),{'status':status,'attempted_window':False},'fixture'),[])
   self.assertEqual(list(Path(tmp).iterdir()),[])

 def test_basis_append_deduplicates_preserves_receipts_and_counters(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/op.BASIS_ROOT
   def packet(oid):
    d={'schema':'qrds.factory.crypto_745_basis_forward_attempt.v1','channel_id':op.basis.CHANNEL_ID,
       'attempted_window':True,'economics_read':False,'source_cost_evidence_sha256':'a'*64,
       'observation':{'observation_id':str(oid),'eligible_for_future_evaluation':True}}
    d['attempt_sha256']=op.sha(json.dumps(d,sort_keys=True,separators=(',',':')).encode());return d
   old=packet(1);op.write(folder/'partitions/old.json',old)
   op.write(folder/'MANIFEST.json',op.basis.build_manifest(folder/'partitions'))
   protected=folder/'partitions/old.json';raw=protected.read_bytes()
   paths=op.apply_basis(root,packet(2),'fixture');self.assertEqual(len(paths),2)
   self.assertEqual(raw,protected.read_bytes())
   m=json.loads((folder/'MANIFEST.json').read_bytes());self.assertEqual(m['eligible_unique_observation_count'],2)
   self.assertFalse(m['economics_read_allowed']);self.assertEqual(m['scientific_credit'],0)
   self.assertEqual(op.apply_basis(root,packet(2),'another'),[])

 def test_actual_git_publication_is_atomic_and_scoped(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);bare=root/'remote.git';repo=root/'repo'
   subprocess.run(['git','init','--bare',str(bare)],check=True,capture_output=True)
   subprocess.run(['git','clone',str(bare),str(repo)],check=True,capture_output=True)
   def g(*args):return op.git(repo,*args)
   g('config','user.name','fixture');g('config','user.email','fixture@example.invalid')
   op.write(repo/'unrelated.json',{'keep':True});g('add','.');g('commit','-m','fixture');g('branch','-M','gate-btc-runtime');g('push','origin','gate-btc-runtime')
   before=g('rev-parse','HEAD').stdout
   def apply(wt):
    p=wt/op.BASIS_ROOT/'LOCAL_TEST.json';op.write(p,{'fixture':True});return [p.relative_to(wt).as_posix()]
   result=op.publish(repo,apply);self.assertTrue(result['changed'])
   self.assertEqual(before,g('rev-parse','HEAD').stdout)
   self.assertEqual(g('show',result['sha']+':unrelated.json').stdout,g('show','HEAD:unrelated.json').stdout)
   self.assertFalse(op.publish(repo,apply)['changed'])
   with self.assertRaisesRegex(ValueError,'SCOPE'):op.publish(repo,lambda wt:['runtime/ledgers/b3_h1/STATUS.json'])

if __name__=='__main__':unittest.main()
