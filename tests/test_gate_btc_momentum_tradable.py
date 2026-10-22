import copy,json,tempfile,unittest
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from tools import gate_btc_momentum_tradable as m

class Provider:
 def __init__(self):
  self.records=[];self.absent=set();self.low=set();self.gaps=set();self.missing=set();self.calls=[];self.multiplier=1
 def metadata(self,a):
  self.calls.append(('metadata',a))
  if a in self.absent:return None
  return {'baseAsset':a,'quoteAsset':'USDT','status':'TRADING','isSpotTradingAllowed':True}
 def bars(self,a,cutoff):
  self.calls.append(('bars',a))
  if a in self.missing:raise m.SourceUnavailable('OUTAGE:'+a)
  rows=[{'date':(date.fromisoformat(cutoff)-timedelta(days=i)).isoformat(),'close':100*self.multiplier,'quote_volume':100 if a in self.low else 2000000} for i in range(30,-1,-1)]
  return rows[:-1] if a in self.gaps else rows

class TradableTests(unittest.TestCase):
 def setUp(self):
  self.policy=json.loads(m.POLICY.read_bytes());self.p=Provider();self.assets=['A'+str(i) for i in range(12)]
 def snap(self,day=0,assets=None):
  assets=assets if assets is not None else self.assets
  return {'cutoff':(date(2026,10,21)+timedelta(days=day)).isoformat(),**{block:{'rows':[{'asset':a,rank:i+1} for i,a in enumerate(assets)]} for block,rank in m.STRATEGIES.values()}}
 def step(self,ledger=None,day=0,assets=None):
  snap=self.snap(day,assets);at=datetime.combine(date.fromisoformat(snap['cutoff'])+timedelta(days=1),datetime.min.time(),timezone.utc)
  return m.advance(ledger,snap,self.p,self.policy,{'signal':'sealed'},at)
 def test_missing_unbought_market_skipped_next_rank_selected(self):
  self.p.absent={'REUSD','USYC','USDGO'};out=self.step(assets=['REUSD','USYC','USDGO']+self.assets)
  for chosen in out['rows'][0]['selected_at_rebalance'].values():self.assertEqual(chosen,self.assets[:10])
  self.assertFalse(any(a in self.p.absent for kind,a in self.p.calls if kind=='bars'))
 def test_short_history_and_low_liquidity_quarantined(self):
  self.p.low={'A0'};self.p.gaps={'A1'};out=self.step();reg=out['state']['registry']
  self.assertEqual(reg['A0']['reason'],'LOW_LIQUIDITY');self.assertEqual(reg['A1']['reason'],'INSUFFICIENT_OR_GAPPED_HISTORY')
  self.assertEqual(reg['A0']['retry_after_cutoff'],'2026-10-24')
 def test_quarantine_expires_and_market_absence_not_permanent_blacklist(self):
  self.p.low={'A0'};_,_,reg,_=m.selections(self.snap(),self.p,self.policy,{})
  self.p.low.clear();_,dec,_,_=m.selections(self.snap(1),self.p,self.policy,reg)
  self.assertEqual(dec['A0']['reason'],'QUARANTINED')
  _,dec,_,_=m.selections(self.snap(3),self.p,self.policy,reg);self.assertTrue(dec['A0']['eligible'])
  self.p.absent={'A0'};out=self.step();self.p.absent.clear()
  _,dec,_,_=m.selections(self.snap(7),self.p,self.policy,out['state']['registry']);self.assertTrue(dec['A0']['eligible'])
 def test_unfilled_slots_remain_cash_not_overweighted(self):
  out=self.step(assets=self.assets[:3]);book=out['state']['books']['M1_TRADABLE_V1']['gross']
  self.assertAlmostEqual(book['cash'],.7);self.assertAlmostEqual(sum(q*100 for q in book['quantities'].values()),.3)
 def test_all_candidates_ineligible_is_cash_not_delivery_failure(self):
  self.p.absent=set(self.assets);out=self.step();self.assertEqual(out['state']['books']['M1_TRADABLE_V1']['net']['cash'],1)
 def test_hold_queries_only_positions_and_keeps_historic_rows(self):
  first=self.step();before=copy.deepcopy(first);self.p.calls=[];second=self.step(first,1,['REUSD']+self.assets)
  self.assertFalse(any(k=='metadata' for k,a in self.p.calls));self.assertNotIn(('bars','REUSD'),self.p.calls)
  self.assertEqual(first,before);self.assertEqual(second['rows'][:-1],first['rows']);self.assertEqual(second['rows'][-1]['event'],'HOLD')
 def test_missing_held_price_blocks_without_mutating_position(self):
  first=self.step();before=copy.deepcopy(first);self.p.missing={'A0'}
  with self.assertRaises(m.SourceUnavailable):self.step(first,1)
  self.assertEqual(first,before)
 def test_outage_not_misclassified_as_illiquidity(self):
  self.p.missing={'A0'}
  with self.assertRaises(m.SourceUnavailable):self.step()
 def test_held_removed_from_ranking_still_valued(self):
  first=self.step();self.p.calls=[];self.step(first,1,self.assets[1:]);self.assertIn(('bars','A0'),self.p.calls)
 def test_seventh_close_rebalances_after_valuing_old_positions(self):
  out=self.step()
  for i in range(1,7):out=self.step(out,i)
  self.p.multiplier=2;out=self.step(out,7,self.assets[2:]);row=out['rows'][-1]
  self.assertEqual(row['event'],'REBALANCE');self.assertAlmostEqual(row['nav_gross']['M1_TRADABLE_V1'],2)
  self.assertEqual(list(out['state']['books']['M1_TRADABLE_V1']['gross']['quantities']),self.assets[2:])
 def test_net_fees_match_btc_and_hold_has_no_turnover(self):
  out=self.step();row=out['rows'][0]
  self.assertAlmostEqual(row['nav_net_modelled']['M1_TRADABLE_V1'],1/1.001);self.assertAlmostEqual(row['btc_nav_net_modelled'],1/1.001)
  self.assertAlmostEqual(row['excess_vs_btc_net_pp']['M1_TRADABLE_V1'],0)
  second=self.step(out,1);self.assertEqual(second['rows'][-1]['trade_costs_this_close']['M1_TRADABLE_V1'],0)
 def test_gap_duplicate_and_policy_mutation_fail_closed(self):
  first=self.step()
  for day in [0,2]:
   with self.assertRaisesRegex(ValueError,'GAP_OR_DUPLICATE'):self.step(first,day)
  self.policy['minimum_median_daily_quote_volume']=1
  with self.assertRaisesRegex(ValueError,'POLICY_AUTHORITY_CHANGED'):self.step(first,1)
 def test_prepolicy_and_duplicate_identity_rejected(self):
  with self.assertRaisesRegex(ValueError,'PRE_POLICY'):self.step(day=-1)
  with self.assertRaisesRegex(ValueError,'DUPLICATE_OR_INVALID'):self.step(assets=['A0','A0'])
 def test_wait_before_policy_does_not_read_source_or_signal(self):
  with tempfile.TemporaryDirectory() as d:
   out=m.run(Path(d)/'absent',Path(d),clock=lambda:datetime(2026,10,21,tzinfo=timezone.utc),provider=self.p)
   self.assertEqual(out['status'],'WAIT_FIRST_POST_POLICY_CLOSE');self.assertEqual(self.p.calls,[])
 def test_capture_idempotency_and_corrupt_source_guard(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap=self.snap();snap['snapshot_sha256']=m.digest((json.dumps(snap,sort_keys=True,separators=(',',':'))+'\n').encode())
   sp=root/'snap.json';sp.write_bytes(m.encoded(snap));clock=lambda:datetime(2026,10,22,4,tzinfo=timezone.utc)
   m.run(sp,root,clock=clock,provider=self.p);before=(root/'LEDGER.json').read_bytes();self.p.calls=[]
   self.assertTrue(m.run(sp,root,clock=clock,provider=self.p)['idempotent']);self.assertEqual(self.p.calls,[])
   self.assertEqual((root/'LEDGER.json').read_bytes(),before);(root/'sources/2026-10-21/RAW.json.gz').write_bytes(b'bad')
   with self.assertRaisesRegex(ValueError,'SEALED_SOURCE'):m.run(sp,root,clock=clock,provider=self.p)
 def test_signal_hash_checked_before_network(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);sp=root/'snap.json';sp.write_bytes(m.encoded(self.snap()))
   with self.assertRaisesRegex(ValueError,'SIGNAL_HASH'):m.run(sp,root,clock=lambda:datetime(2026,10,22,tzinfo=timezone.utc),provider=self.p)
   self.assertEqual(self.p.calls,[])

class TransitionTests(unittest.TestCase):
 def test_legacy_retirement_preserves_exact_ledger_and_skips_prices(self):
  from tools import gate_btc_momentum_hold_epoch as h
  from argparse import Namespace
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);config=h.load_json(h.APPROVAL)
   for name in config['legacy_seals']:
    (root/name).write_bytes(b'{"legacy":true}\n');config['legacy_seals'][name]=h.digest((root/name).read_bytes())
   cp=root/'approval.json';h.save(cp,config);epoch=h.setup(root,config,h.load_json(h.CONTRACT))
   before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
   args=Namespace(ledger_dir=root,snapshot=root/'missing-signal',output_zip=root/'px.zip',phase='prepare')
   with patch.object(h,'APPROVAL',cp),patch('tools.gate_btc_momentum_required_prices.collect') as collect:
    out=h.run(args,clock=lambda:datetime(2026,10,22,tzinfo=timezone.utc));collect.assert_not_called()
   self.assertEqual(out['status'],'CLOSED_RULE_VERSION_SUPERSEDED')
   self.assertTrue(out['prior_failed_rebalance_preserved'])
   for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)
 def test_reporting_keeps_old_and_new_series_separate_and_failure_visible(self):
  from tools.gate_btc_reporting_operational_overlay import enrich
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);status={**m.SAFETY,'schema':'gate_btc.momentum_tradable_status.v1','status':'BLOCKED_TRADABLE_DELIVERY','last_valid_cutoff':'2026-10-21','return_observations':0,'error':'HELD_PRICE_MISSING'}
   m.save(root/'ledgers/momentum_tradable_v1/STATUS.json',status)
   out=enrich(root,{'reference_data_date':'2026-10-22'},as_of_utc=datetime(2026,10,23,tzinfo=timezone.utc))
   self.assertIn('momentum_m1_m2',out['components']);self.assertIn('momentum_tradable_v1',out['components'])
   self.assertIn('momentum_tradable_v1',out['warnings']['failed_delivery_components'])
 def test_reporting_wait_is_green_only_before_policy_close(self):
  from tools.gate_btc_reporting_operational_overlay import enrich
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);status={**m.SAFETY,'schema':'gate_btc.momentum_tradable_status.v1','status':'WAIT_FIRST_POST_POLICY_CLOSE','first_eligible_cutoff':'2026-10-21','return_observations':0}
   m.save(root/'ledgers/momentum_tradable_v1/STATUS.json',status)
   first=enrich(root,{},as_of_utc=datetime(2026,10,21,tzinfo=timezone.utc))
   late=enrich(root,{},as_of_utc=datetime(2026,10,22,tzinfo=timezone.utc))
   self.assertEqual(first['components']['momentum_tradable_v1']['collection_health_hint'],'GREEN_ACTIVE')
   self.assertEqual(late['components']['momentum_tradable_v1']['collection_health_hint'],'AMBER_BLOCKED_DEPENDENCY')
 def test_workflow_runs_new_shadow_and_publishes_its_actual_failure(self):
  workflow=(m.ROOT/'.github/workflows/gate-btc-momentum-shadow.yml').read_text()
  self.assertIn('python tools/gate_btc_momentum_tradable.py',workflow)
  self.assertIn('git -C runtime_repo add runtime/ledgers/momentum_tradable_v1',workflow)
  self.assertIn('steps.tradable.outcome',workflow)

if __name__=='__main__':unittest.main()
