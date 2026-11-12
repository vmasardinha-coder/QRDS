import hashlib,json,tempfile,unittest
from pathlib import Path
from tools.gate_btc_factory.crypto_745_basis_checkpoint_binding import bind,write_once
from tests.test_gate_btc_crypto_745_basis_forward_capture import pair,receipt

class BindingTests(unittest.TestCase):
 def fixture(self,root,n=61,legacy=False):
  (root/'partitions').mkdir();parts=[]
  for i in range(n):
   settle=2000000+i*28800000;decision=settle-300000
   pre=pair(decision-1000,decision-1000);entry=pair(decision+1,decision+1);exit=pair(settle,settle)
   funding=dict(instId='BTC-USDT-SWAP',funding_time_ms=settle,ts_ms=decision-1000,receipt=receipt(decision-1000),funding_rate='0.0001')
   if legacy and i==0:
    pre.pop('spot_receipt');pre.pop('perp_receipt');funding.pop('receipt')
   o=dict(observation_id=str(settle),decision_ms=decision,settlement_ms=settle,eligible_for_future_evaluation=True,predecision_pair=pre,entry_pair=entry,exit_pair=exit,funding_bound=funding)
   d=dict(channel_id='CRYPTO_SPOT_PERP_BASIS_FUNDING',economics_read=False,scientific_credit=0,quote_samples_decision_window=[pre,entry],quote_samples_exit_window=[exit],funding_samples_decision_window=[funding],observation=o)
   raw=json.dumps(d).encode();name=str(i)+'.json';(root/'partitions'/name).write_bytes(raw)
   parts.append(dict(file=name,sha256=hashlib.sha256(raw).hexdigest(),eligible=True,observation_id=str(settle)))
  (root/'MANIFEST.json').write_text(json.dumps(dict(channel_id='CRYPTO_SPOT_PERP_BASIS_FUNDING',economics_read=False,partitions=list(reversed(parts)),source_cost_evidence_sha256='sealed')))
 def test_original60_bound_without_outcome_metrics(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r);z=bind(r,'pinned');self.assertEqual(z['status'],'BOUND_ORIGINAL_N60');self.assertEqual(len(z['records']),60);self.assertFalse(z['economics_read_allowed']);self.assertEqual(z['records'][0]['file'],'0.json')
 def test_legacy_missing_receipts_not_replaced_by_61st(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r,legacy=True);z=bind(r,'pinned');self.assertEqual(z['status'],'ORIGINAL_N60_NOT_ADMISSIBLE');self.assertEqual(z['causally_admissible_count'],59);self.assertEqual(len(z['records']),60)
 def test_tampered_bytes_fail(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r);(r/'partitions/0.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'BYTES_CHANGED'):bind(r,'pinned')
 def test_incomplete_population_waits(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);self.fixture(r,20);self.assertEqual(bind(r,'pinned')['status'],'WAIT_ORIGINAL_N60')
 def test_binding_is_immutable(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'binding.json';write_once(p,{'a':1});write_once(p,{'a':1})
   with self.assertRaisesRegex(ValueError,'IMMUTABLE'):write_once(p,{'a':2})
