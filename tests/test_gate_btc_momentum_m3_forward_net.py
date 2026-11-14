import copy,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from tools import gate_btc_momentum_m3_forward_net as forward
from tools import gate_btc_momentum_canonical_net as net

class ForwardNetTests(unittest.TestCase):
 def setUp(self):
  self.c=net.read(forward.BINDING)
  self.a={'first_eligible_cutoff':'2026-11-06','contract_sha256':self.c['gross_contract_sha256']}
  self.c['gross_activation_sha256']=net.sha(net.packed(self.a))
  self.at=datetime(2026,11,5,14,tzinfo=timezone.utc)
 def fixture(self):
  assets=['A'+str(i) for i in range(10)];rows=[];marks=[]
  for i in range(2):
   prices={a:1+i*.1 for a in assets};prices['BTC']=1+i*.05;marks.append(prices)
   rows.append(dict(cutoff='2026-11-0'+str(6+i),event='ACTIVATION' if not i else 'HOLD',return_observations=i,nav={'M3_TOP10':1+i*.1},btc_nav=prices['BTC'],quantities_after_close={'M3_TOP10':{a:.1 for a in assets}},holdings_after_close={'M3_TOP10':assets},evidence={'source_available_at_utc':'2026-11-0'+str(7+i)+'T07:00:00+00:00'}))
  return {'rows':rows},marks
 def test_pre_admission_is_idempotent_and_does_not_write_gross_or_old_net(self):
  with tempfile.TemporaryDirectory() as d:
   runtime=Path(d);epoch=runtime/'runtime/ledgers'/self.c['gross_epoch'];net.immutable(epoch/'ACTIVATION.json',self.a)
   old=runtime/'runtime/ledgers/momentum_canonical_net/old.json';net.immutable(old,{'old':1});before=old.read_bytes()
   one=forward.run(runtime,self.c,self.at);two=forward.run(runtime,self.c,self.at)
   self.assertEqual(one['status'],'WAITING_FIRST_FUTURE_COMPLETED_CLOSE');self.assertEqual(one,two)
   self.assertEqual(old.read_bytes(),before);self.assertFalse((epoch/'LEDGER.json').exists())
   self.assertFalse(list(runtime.rglob('observations/*.json')))
 def test_late_admission_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'NO_LATE'):forward.admit(Path(d),self.c,datetime(2026,11,7,tzinfo=timezone.utc))
 def test_changed_rate_or_epoch_rejected(self):
  for key,value in [('one_way_total_cost_bps',5),('gross_epoch','momentum_m3_economics'),('gross_activation_sha256','0'*64)]:
   c=copy.deepcopy(self.c);c[key]=value
   with self.assertRaisesRegex(ValueError,'BINDING_CHANGED'):forward.validate_binding(c,net.read(net.CONTRACT),self.a)
 def test_shared_accounting_preserves_old_math_and_new_entry_cost(self):
  ledger,prices=self.fixture();before=copy.deepcopy((ledger,prices));new=net.calculate_bound(ledger,prices,'2026-11-06',.001)
  for i,row in enumerate(ledger['rows']):row['cutoff']='2026-10-'+str(17+i)
  old=net.calculate(ledger,prices,net.read(net.CONTRACT))
  self.assertEqual([r['portfolios'] for r in new],[r['portfolios'] for r in old])
  for name in ['M3_TOP10','BTC_HOLD']:self.assertAlmostEqual(new[0]['portfolios'][name]['nav_net_model'],1/1.001)
  self.assertEqual(new[1]['portfolios']['M3_TOP10']['cost_nav_units'],0)
  self.assertEqual(prices,before[1])
 def test_one_current_row_idempotent_and_sealed_prefix_tamper_rejected(self):
  l,p=self.fixture();rows=net.calculate_bound(l,p,'2026-11-06',.001)
  with tempfile.TemporaryDirectory() as d:
   out=Path(d);at=datetime(2026,11,7,12,tzinfo=timezone.utc)
   forward.append_current(out,rows[:1],'seal',at);forward.append_current(out,rows[:1],'seal',at)
   self.assertEqual(len(list((out/'observations').glob('*.json'))),1)
   changed=copy.deepcopy(rows[:1]);changed[0]['event']='WRONG'
   with self.assertRaisesRegex(ValueError,'SEALED'):forward.append_current(out,changed,'seal',at)
 def test_no_missing_days_backfill(self):
  l,p=self.fixture();rows=net.calculate_bound(l,p,'2026-11-06',.001)
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'NO_BACKFILL'):forward.append_current(Path(d),rows,'seal',datetime(2026,11,8,tzinfo=timezone.utc))
 def test_old_price_publication_rejected(self):
  l,p=self.fixture();rows=net.calculate_bound(l,p,'2026-11-06',.001);rows[0]['source_evidence']['source_available_at_utc']='2026-11-06T07:00:00+00:00'
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'NOT_CURRENT'):forward.append_current(Path(d),rows[:1],'seal',datetime(2026,11,7,tzinfo=timezone.utc))

 def test_later_gross_start_is_visible_blocked_without_rebinding_or_returns(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   runtime=Path(d);epoch=runtime/'runtime/ledgers'/self.c['gross_epoch']
   net.immutable(epoch/'ACTIVATION.json',self.a)
   net.immutable(epoch/'LEDGER.json',{'frozen_gross':'untouched'})
   out=runtime/'runtime/ledgers/momentum_m3_forward_net'/forward.SERIES
   forward.admit(out,self.c,self.at)
   admission=(out/'ADMISSION.json').read_bytes();binding=(out/'BINDING.json').read_bytes()
   gross=(epoch/'LEDGER.json').read_bytes()
   late={'rows':[{'cutoff':'2026-11-11'}]}
   with patch.object(net,'load_verified',return_value=(late,[])):
    at=datetime(2026,11,12,12,tzinfo=timezone.utc)
    one=forward.run(runtime,self.c,at);two=forward.run(runtime,self.c,at)
   self.assertEqual(one,two)
   self.assertEqual(one['status'],'BLOCKED_BOUND_GROSS_ACTIVATION_MISSED')
   self.assertEqual(one['return_observations'],0)
   self.assertEqual(one['first_activation_cutoff'],'2026-11-06')
   self.assertEqual(one['actual_gross_activation_cutoff'],'2026-11-11')
   self.assertFalse(one['net_returns_available'])
   self.assertFalse(list(out.glob('observations/*.json')))
   self.assertEqual((out/'ADMISSION.json').read_bytes(),admission)
   self.assertEqual((out/'BINDING.json').read_bytes(),binding)
   self.assertEqual((epoch/'LEDGER.json').read_bytes(),gross)

if __name__=='__main__':unittest.main()
