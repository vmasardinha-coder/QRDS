import sys,pathlib,unittest,tempfile,json
from datetime import datetime,timedelta
P=pathlib.Path(__file__).resolve().parents[1]
sys.path[:0]=[str(P/'code'),str(P/'frozen_source')]
import pressure_valve_expanded as pv
import pressure_valve_expanded_report as report
import gate_btc_2_item3b_forward_source_probe as source
import gate_btc_2_item3c_forward_collector as engine
from unittest.mock import patch
DAY='2026-10-22'
def bars():
 return [{'timestamp':pv.at(DAY,i*5).isoformat(),'open':200000+i*5,'high':200010+i*5,'low':199990+i*5,'close':200005+i*5,'real_volume':100,'tick_volume':100} for i in range(115)]
def contract():return {'family_id':'H518','feature':'REALIZED_VOL','decision_window_minutes':90,'direction':'REVERSION','standardization_lookback_sessions':10,'abs_z_threshold':.75,'holding_horizons_minutes':[30,60,120]}
class Expanded(unittest.TestCase):
 def test_audit_exclusive(self):
  c=json.loads((P/'CONFIG.json').read_text());fs=c['families'];self.assertEqual(len({f['contract']['family_id'] for f in fs}),580);self.assertEqual(sum(f['policy']==pv.STRICT for f in fs),26);self.assertEqual(sum(f['initial_eligibility']=='READY' and f['policy']==pv.DIAG for f in fs),490);self.assertEqual(sum(f['initial_eligibility']!='READY' for f in fs),64)
 def test_costs_and_h518_timing(self):
  o=pv.outcome(contract(),bars(),DAY,1,120,source,.2);self.assertEqual(o['entry_timestamp'][11:16],'10:30');self.assertEqual(o['exit_timestamp'][11:16],'12:30');self.assertEqual(o['delayed_exit_timestamp'][11:16],'12:35');self.assertAlmostEqual(o['gross_bps']-o['net_ref_2bps'],2);self.assertAlmostEqual(o['gross_bps']-o['net_stress_3bps'],3);self.assertAlmostEqual(o['cost_ref_brl'],o['entry_price']*.2*.0002)
 def test_h618_timing(self):
  c=contract();c.update(family_id='H618',decision_window_minutes=15);o=pv.outcome(c,bars(),DAY,-1,120,source,.2);self.assertEqual(o['entry_timestamp'][11:16],'09:15');self.assertEqual(o['delayed_exit_timestamp'][11:16],'11:20')
 def test_bad_trade_path_does_not_create_zero(self):
  rs=bars();del rs[40];o=pv.outcome(contract(),rs,DAY,1,120,source,.2);self.assertEqual(o['state'],'OUTCOME_DATA_UNAVAILABLE');self.assertNotIn('net_ref_2bps',o)
 def test_later_gap_does_not_invalidate_feature_window(self):
  rs=bars();del rs[80];v,q,_=pv.feature_values(rs,DAY,'2026-12-16',None,['REALIZED_VOL|90'],source,engine,True);self.assertIsNotNone(v[pv.DIAG]['REALIZED_VOL|90']);self.assertIsNone(v[pv.STRICT]['REALIZED_VOL|90'])
 def test_strict_cannot_finalize_morning(self):
  r=pv.evaluate(contract(),pv.STRICT,{'REALIZED_VOL|90':3},{},bars(),DAY,source,engine,{},True,.2);self.assertEqual(r['state'],'PENDING_SESSION_QA');self.assertEqual(r['outcomes'],[])
 def test_zero_dispersion_distinct_from_missing_history(self):
  h=[{'session':'2026-10-20','value':1} for _ in range(10)];r=pv.evaluate(contract(),pv.DIAG,{'REALIZED_VOL|90':2},{'REALIZED_VOL|90':h},bars(),DAY,source,engine,{});self.assertEqual(r['reason'],'ZERO_DISPERSION');self.assertEqual(r['missing'],0)
 def test_no_signal_is_not_data_failure(self):
  h=[{'session':'2026-10-20','value':i} for i in range(10)];r=pv.evaluate(contract(),pv.DIAG,{'REALIZED_VOL|90':4.5},{'REALIZED_VOL|90':h},bars(),DAY,source,engine,{});self.assertEqual(r['state'],'NO_SIGNAL')
 def test_history_cannot_include_current_session(self):
  with tempfile.TemporaryDirectory() as t:
   seed={'histories':{pv.STRICT:{'x':[{'session':DAY,'value':1}]},pv.DIAG:{}},'last_strict_close':None}
   with self.assertRaises(AssertionError):pv.build_histories(pathlib.Path(t),seed,DAY)
 def test_immutable_conflict(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'a.json';pv.immutable(p,{'a':1});pv.immutable(p,{'a':1})
   with self.assertRaises(RuntimeError):pv.immutable(p,{'a':2})
 def test_basket_alternatives_and_incomplete(self):
  c=contract();o=pv.outcome(c,bars(),DAY,1,60,source,.2);rec={'session':DAY,'policy':pv.STRICT,'families':[{'family_id':'H518','state':'TRIGGER','outcomes':[o]}]};b={'name':'x','policy':pv.STRICT,'families':['H518'],'selection_rule':'fixed'}
  x=report.basket_sim([rec],b,60,'REF',{DAY:{'rows':bars()}});self.assertEqual(x['closed_positions'],1);self.assertAlmostEqual(x['net_brl'],o['gross_brl']-o['cost_ref_brl']);self.assertEqual(x['max_gross_contracts'],1)
  y=report.basket_sim([rec],b,30,'REF',{DAY:{'rows':bars()}});self.assertIsNone(y['net_brl']);self.assertEqual(y['closed_positions'],0)
 def test_no_data_correlation_unavailable(self):self.assertIsNone(report.corr([],[]));self.assertIsNone(report.corr([0,0],[0,0]))
 def test_time_binding_after_market_does_not_need_fresh_tick(self):
  now=datetime.fromisoformat(DAY+'T19:15:00-03:00');epoch=int(datetime.fromisoformat(DAY+'T18:30:00+00:00').timestamp());ev={'raw_tick_epoch':epoch,'fresh_within_900s':False}
  self.assertEqual(pv.bound_time_mode(now,'BROKER_LOCAL_EPOCH',ev,'BROKER_LOCAL_EPOCH',source),'BROKER_LOCAL_EPOCH')
  with self.assertRaises(AssertionError):pv.bound_time_mode(datetime.fromisoformat(DAY+'T12:45:00-03:00'),'BROKER_LOCAL_EPOCH',ev,'BROKER_LOCAL_EPOCH',source)
  with self.assertRaises(AssertionError):pv.bound_time_mode(now,'UTC_EPOCH',{'fresh_within_900s':True},'BROKER_LOCAL_EPOCH',source)
 def test_capture_activation_isolation_and_idempotency(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);c=contract();cfg={'activation_date':DAY,'families':[{'contract':c,'policy':pv.DIAG}]}
   hist=[{'session':f'2026-10-{i:02}','value':float(i)} for i in range(1,11)]
   seed={'cutoff':'2026-10-21','histories':{pv.STRICT:{},pv.DIAG:{'REALIZED_VOL|90':hist}},'last_strict_close':None,'config_hash':pv.digest(cfg)}
   pv.save(root/'CONFIG.json',cfg);pv.save(root/'initialization/SEED.json',seed)
   snapshot=(bars()[:45],bars()[:45],{'symbol':'WINZ26','expiration_time':int(datetime.fromisoformat('2026-12-16T23:59:00-03:00').timestamp())},{'point_value_brl':.2,'margin':{}})
   with patch.object(pv,'frozen',return_value=(source,engine)),patch.object(pv,'snapshot_mt5',return_value=snapshot):
    with self.assertRaises(RuntimeError):pv.capture(root,'morning',datetime.fromisoformat('2026-10-21T12:45:00-03:00'))
    pv.capture(root,'morning',datetime.fromisoformat(DAY+'T12:45:00-03:00'))
    f=root/'ledger'/pv.DIAG/(DAY+'.json');before=f.read_bytes()
    pv.capture(root,'morning',datetime.fromisoformat(DAY+'T12:55:00-03:00'))
    self.assertEqual(f.read_bytes(),before);self.assertFalse((root/'ledger'/pv.STRICT/(DAY+'.json')).exists());self.assertEqual(len(list((root/'ledger'/pv.DIAG).glob('*.json'))),1)
if __name__=='__main__':unittest.main()
