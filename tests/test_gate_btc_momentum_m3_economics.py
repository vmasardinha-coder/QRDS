import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from tools import gate_btc_momentum_m3_economics as e

C=e.read(e.CONTRACT)
A={'first_eligible_cutoff':'2026-09-28'}
def signal(day=0,reverse=False):
    rows=[{'asset':f'A{i:03}', 'm3':float(i if reverse else 40-i)} for i in range(40)]
    top=[r['asset'] for r in sorted(rows,key=lambda r:(-r['m3'],r['asset']))[:10]]
    s={'candidate_id':e.CANDIDATE_ID,'cutoff':(datetime(2026,9,28)+timedelta(days=day)).date().isoformat(),
       'common_universe_n':40,'retrospective_credit':0,'rows':rows,'selection_preview':top}
    s['snapshot_sha256']=e.canonical_sha(s);return s
def at(day=0): return datetime(2026,9,29,tzinfo=timezone.utc)+timedelta(days=day)
def prices(): return {**{f'A{i:03}':100.0 for i in range(40)},'BTC':100.0}
def step(l=None,day=0,p=None,reverse=False,evidence=None):
    return e.advance(l,signal(day,reverse),p or prices(),A,C,evidence or {'id':day},at(day))

class Economics(unittest.TestCase):
    def test_activation_is_zero_return_observations_and_no_capital(self):
        l=step();self.assertEqual(l['state']['nav'],1);self.assertEqual(l['state']['return_observations'],0)
        self.assertIsNone(l['rows'][0]['daily_return_gross']);self.assertEqual(l['orders'],0)
        self.assertEqual(l['real_capital'],0);self.assertEqual(l['rows'][0]['cost_status'],'N_D')
    def test_quantities_hold_after_rank_change_and_nav_drifts(self):
        l=step();q=copy.deepcopy(l['state']['quantities']);p=prices();p['A000']=200
        l=step(l,1,p,True);self.assertEqual(l['state']['quantities'],q)
        self.assertAlmostEqual(l['state']['nav'],1.1);self.assertEqual(l['rows'][-1]['event'],'HOLD')
        l=step(l,2,p,True);self.assertAlmostEqual(l['state']['nav'],1.1)
    def test_seventh_close_revalues_old_holdings_then_rebalances(self):
        l=step();p=prices();p['A000']=200
        for i in range(1,8): l=step(l,i,p,True)
        self.assertEqual(l['rows'][-1]['event'],'REBALANCE')
        self.assertEqual(set(l['state']['quantities']),set(signal(7,True)['selection_preview']))
        self.assertAlmostEqual(l['state']['nav'],1.1)
    def test_btc_is_independent_buy_hold(self):
        l=step();p=prices();p['BTC']=120;l=step(l,1,p)
        self.assertEqual(l['state']['btc_nav'],1.2);self.assertAlmostEqual(l['rows'][-1]['excess_vs_btc_percentage_points'],-20)
    def test_missing_dropped_held_asset_fails_without_state_mutation(self):
        l=step();before=copy.deepcopy(l);p=prices();del p['A000']
        with self.assertRaisesRegex(ValueError,'HELD_PRICES'):step(l,1,p,True)
        self.assertEqual(l,before)
    def test_gap_and_old_cutoff_rejected(self):
        with self.assertRaisesRegex(ValueError,'GAP'):step(step(),2)
        with self.assertRaisesRegex(ValueError,'NON_PROSPECTIVE'):e.advance(None,signal(),prices(),A,C,{},at(1))
    def test_duplicate_idempotence_and_changed_evidence_rejected(self):
        l=step();self.assertEqual(step(l),l)
        with self.assertRaisesRegex(ValueError,'EVIDENCE_CHANGED'):step(l,evidence={'changed':True})
    def test_corrupt_signal_and_state_rejected(self):
        s=signal();s['rows'][0]['m3']=1000
        with self.assertRaisesRegex(ValueError,'HASH'):e.advance(None,s,prices(),A,C,{},at())
        l=step();l['state']['nav']=2
        with self.assertRaises(ValueError):step(l,1)
    def test_arming_reads_no_history_or_prices(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'econ'
            with patch.object(e,'collect',side_effect=AssertionError('no collection')):
                s=e.run(root,Path(td)/'missing_signals',Path(td)/'missing_sources',at=at())
            self.assertEqual(s['status'],'WAITING_FIRST_POST_IMPLEMENTATION_CLOSE')
            self.assertFalse((root/'LEDGER.json').exists())
            self.assertEqual(e.read(root/'ACTIVATION.json')['historical_signal_credit'],0)
    def test_missing_current_signal_publishes_failure_without_fake_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'econ';e.run(root,Path(td),Path(td),at=at())
            with self.assertRaisesRegex(ValueError,'SIGNAL_MISSING'):e.run(root,Path(td),Path(td),at=at(1))
            self.assertEqual(e.read(root/'STATUS.json')['status'],'FAILED_M3_ECONOMIC_DELIVERY')
            self.assertFalse((root/'LEDGER.json').exists())
    def test_future_and_changed_contract_rejected(self):
        with self.assertRaises(ValueError):e.advance(None,signal(1),prices(),A,C,{},at())
        c=copy.deepcopy(C);c['economic_shadow_contract']['between_rebalances']='DAILY_RESET'
        with self.assertRaisesRegex(ValueError,'CONTRACT_CHANGED'):e.advance(None,signal(),prices(),A,c,{},at())


    def test_real_causal_binding_full_delivery_and_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'econ';sources=Path(td)/'source';signals=Path(td)/'signals'
            sources.mkdir();signals.mkdir()
            e.run(root,signals,sources,at=at(-1))
            for lag in (0,7,14):
                cutoff=(datetime(2026,9,28)-timedelta(days=lag)).date().isoformat()
                obj={'cutoff':cutoff,'safety':e.SAFETY,
                     'm1':{'rows':[{'asset':f'A{i:03}','r30':float(40-i)} for i in range(40)]}}
                obj['snapshot_sha256']=e.canonical_sha(obj);e.save(sources/(cutoff+'.json'),obj)
            snap=e.compute(sources,'2026-09-28');e.save(signals/'2026-09-28.json',snap)
            def collector(snap,state,folder,output,**kwargs):
                self.assertEqual(set(kwargs['assets']),set(snap['selection_preview'])|{'BTC'})
                dest=folder/snap['cutoff'];dest.mkdir(parents=True)
                for name in ('required_prices.zip','RAW_SOURCES.json.gz'): (dest/name).write_bytes(b'sealed')
                m={'cutoff':snap['cutoff'],'available_at_utc':at().isoformat(),
                   'prices':[{'symbol':a,'close_usd':100.0} for a in kwargs['assets']],
                   'prices_zip_sha256':e.sha(b'sealed'),'raw_archive_sha256':e.sha(b'sealed')}
                e.save(dest/'MANIFEST.json',m);return m
            result=e.run(root,signals,sources,at=at(),collector=collector)
            self.assertEqual(result['return_observations'],0)
            before=(root/'LEDGER.json').read_bytes()
            result=e.run(root,signals,sources,at=at(),collector=lambda *a,**kw:self.fail('duplicate fetch'))
            self.assertTrue(result['idempotent']);self.assertEqual((root/'LEDGER.json').read_bytes(),before)
            obj=e.read(sources/'2026-09-21.json');obj['m1']['rows'][0]['r30']=999
            e.save(sources/'2026-09-21.json',obj)
            with self.assertRaises(SystemExit): e.run(root,signals,sources,at=at(),collector=collector)
            self.assertEqual((root/'LEDGER.json').read_bytes(),before)


    def test_reporting_wait_expires_and_failure_is_visible(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);econ=root/'ledgers/momentum_m3_economics'
            e.report(econ,'WAITING_FIRST_POST_IMPLEMENTATION_CLOSE',A)
            view=enrich(root,{},as_of_utc=at(-1))['components']['momentum_m3_economics']
            self.assertEqual(view['freshness'],'CURRENT_CALENDAR_GATED')
            view=enrich(root,{},as_of_utc=at())['components']['momentum_m3_economics']
            self.assertNotEqual(view['collection_health_hint'],'GREEN_ACTIVE')
            e.report(econ,'FAILED_M3_ECONOMIC_DELIVERY',A,error='missing held asset')
            v=enrich(root,{},as_of_utc=at())
            self.assertIn('momentum_m3_economics',v['warnings']['failed_delivery_components'])

if __name__=='__main__':unittest.main()
