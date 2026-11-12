import json,tempfile,unittest
from pathlib import Path
from tools.gate_btc_h31_fixed_checkpoint import checkpoint,digest,write_once

class CheckpointTests(unittest.TestCase):
 def freeze(self):return dict(checkpoints=[10,20,40],rule_hash_sha256='a'*64,trigger_abs_standardized_impulse_gte=1.5,reference_roundtrip_cost_bp=2,stress_roundtrip_cost_bp=3)
 def records(self,n=10):
  rows=[]
  for i in range(1,n+1):
   trigger=i%2==0;gross=10 if trigger else None
   rows.append(dict(date=f'2026-09-{i:02}',freeze_rule_hash_sha256='a'*64,h1_economics_read=False,orders=0,real_capital=0,engine_feed=False,warmup=dict(trailing_session_dates=[f'2026-08-{j:02}' for j in range(1,21)],uses_scored_prospective_rows_for_warmup=False),signal=dict(standardized_impulse=2 if trigger else .1,wdo_ret30_bps=1,trigger=trigger,side=-1 if trigger else 0),sealed_economics=dict(gross_bps=gross,reference_net_bps=8 if trigger else None,stress_net_bps=7 if trigger else None)))
  return rows
 def write(self,r,rows):
  (r/'events').mkdir(exist_ok=True);last=None
  for row in rows:
   row=dict(row);row['previous_event_hash']=last;row['event_hash_sha256']=digest(row);last=row['event_hash_sha256'];(r/'events'/(row['date']+'.json')).write_text(json.dumps(row))
  (r/'STATUS.json').write_text(json.dumps(dict(eligible_observations=len(rows),last_event_hash=last,latest_date=rows[-1]['date'])))
 def test_complete_checkpoint_without_invented_portfolio_return(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);self.write(r,self.records());z=checkpoint(r,self.freeze());self.assertEqual(z['trades'],5);self.assertEqual(z['reference_net_bps_sum'],40);self.assertIsNone(z['portfolio_return']);self.assertFalse(z['h1_economics_read'])
 def test_nine_observations_never_expose_partial_economics(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);self.write(r,self.records(9))
   with self.assertRaisesRegex(ValueError,'NO_PARTIAL'):checkpoint(r,self.freeze())
 def test_tampered_event_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);self.write(r,self.records());p=r/'events/2026-09-01.json';d=json.loads(p.read_text());d['orders']=1;p.write_text(json.dumps(d))
   with self.assertRaisesRegex(ValueError,'HASH_CHAIN'):checkpoint(r,self.freeze())
 def test_resealed_safety_violation_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);rows=self.records();rows[0]['h1_economics_read']=True;self.write(r,rows)
   with self.assertRaisesRegex(ValueError,'AUTHORITY'):checkpoint(r,self.freeze())
 def test_cost_change_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);rows=self.records();rows[1]['sealed_economics']['reference_net_bps']=9;self.write(r,rows)
   with self.assertRaisesRegex(ValueError,'COST'):checkpoint(r,self.freeze())
 def test_noncausal_warmup_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);rows=self.records();rows[0]['warmup']['trailing_session_dates'][-1]='2026-09-01';self.write(r,rows)
   with self.assertRaisesRegex(ValueError,'NONCAUSAL'):checkpoint(r,self.freeze())
 def test_original_checkpoint_unchanged_after_new_observation(self):
  with tempfile.TemporaryDirectory() as td:
   r=Path(td);self.write(r,self.records(10));first=checkpoint(r,self.freeze());self.write(r,self.records(11));self.assertEqual(checkpoint(r,self.freeze()),first)
 def test_checkpoint_output_is_immutable(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'checkpoint.json';write_once(p,{'n':10});write_once(p,{'n':10})
   with self.assertRaisesRegex(ValueError,'IMMUTABLE'):write_once(p,{'n':11})
