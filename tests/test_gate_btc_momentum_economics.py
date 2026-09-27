import contextlib,copy,io,json,tempfile,unittest,zipfile
from argparse import Namespace
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from tools import gate_btc_momentum_economic_shadow as e
from tools import gate_btc_momentum_required_prices as p

class MomentumEconomicsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.now=datetime(2026,9,27,20,tzinfo=timezone.utc)
        self.snapshot={'cutoff':'2026-09-26','m1':{'rows':[{'asset':f'A{i:02d}','rank_m1':i+1} for i in range(10)]},'m2':{'rows':[{'asset':f'A{i:02d}','rank_m2':i+1} for i in range(10)]}}
        self.state={'last_cutoff':'2026-09-13','holdings':{n:['LSK']+[f'A{i:02d}' for i in range(9)] for n in e.STRATS}}
        self.calls=[]
    def loader(self,session,symbol):
        self.calls.append(symbol)
        return pd.DataFrame([{'date':pd.Timestamp('2026-09-26'),'symbol':symbol,'close_usd':.3408}])
    def collect(self,loaders=None):
        return p.collect(self.snapshot,self.state,self.root/'prices',self.root/'quotes.zip',clock=lambda:self.now,loaders=loaders or [('cdd',self.loader)])
    def test_held_asset_required_outside_current_universe(self):
        required=p.required_assets(self.snapshot,self.state)
        self.assertIn('LSK',required);self.assertIn('BTC',required);self.assertEqual(len(required),12)
        manifest=self.collect();self.assertIn('LSK',self.calls)
        self.assertEqual(e.extract_prices(self.root/'quotes.zip','2026-09-26')['LSK'],.3408)
        self.assertEqual(manifest['scientific_credit'],0)
    def test_same_cutoff_does_not_fetch_or_replace_sources(self):
        first=self.collect();self.calls=[]
        second=self.collect();self.assertEqual(first,second);self.assertEqual(self.calls,[])
    def test_corrupt_archive_blocks_idempotent_success(self):
        self.collect();(self.root/'prices/2026-09-26/required_prices.zip').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'ARCHIVE_CORRUPT'):self.collect()
    def test_stale_primary_falls_back_only_to_real_current_quote(self):
        def stale(session,symbol):return pd.DataFrame([{'date':'2026-09-25','symbol':symbol,'close_usd':1.}])
        manifest=self.collect([('cdd',stale),('binance',self.loader)])
        self.assertTrue(all(r['source']=='binance' for r in manifest['prices']))
    def test_missing_quote_is_not_zero_or_forward_filled(self):
        def missing(session,symbol):raise ValueError('no data')
        with self.assertRaisesRegex(ValueError,'MISSING_REQUIRED_PRICES'):self.collect([('cdd',missing)])
        self.assertFalse((self.root/'quotes.zip').exists())
    def test_backfill_is_not_accepted(self):
        self.snapshot['cutoff']='2026-09-14'
        with self.assertRaisesRegex(ValueError,'NO_BACKFILL'):self.collect()
    def test_duplicate_or_nonfinite_prices_fail(self):
        f=pd.DataFrame([{'date':'2026-09-26','symbol':'LSK','close_usd':float('inf')}])
        with self.assertRaisesRegex(ValueError,'INVALID'):p.choose_quote(f,'LSK','2026-09-26')
        f=pd.DataFrame([{'date':'2026-09-26','symbol':'LSK','close_usd':v} for v in [1,2]])
        with self.assertRaisesRegex(ValueError,'CONFLICTING'):p.choose_quote(f,'LSK','2026-09-26')
    def test_existing_and_current_gaps_are_all_exposed(self):
        hist={'rows':[{'cutoff':d} for d in ['2026-09-04','2026-09-06','2026-09-07','2026-09-08','2026-09-09','2026-09-10','2026-09-12','2026-09-13']]}
        before=copy.deepcopy(hist);result=e.preflight(self.state,hist,'2026-09-26')
        self.assertEqual([x['missing_closes'] for x in result['gaps']],[1,1,12]);self.assertEqual(hist,before)
    def test_failed_economics_preserves_original_files_byte_for_byte(self):
        e.write_json(self.root/'STATE.json',self.state);e.write_json(self.root/'HISTORY.json',{'rows':[{'cutoff':'2026-09-13'}]});e.write_json(self.root/'snap.json',self.snapshot)
        before={n:(self.root/n).read_bytes() for n in ('STATE.json','HISTORY.json')}
        args=Namespace(snapshot=self.root/'snap.json',ledger_dir=self.root,v2a_zip=self.root/'missing.zip')
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(e.evaluate(args),2)
        self.assertEqual(before,{n:(self.root/n).read_bytes() for n in before})
        self.assertEqual(e.load_json(self.root/'DELIVERY_STATUS.json')['status'],'BLOCKED_GAP_DISPOSITION_REQUIRED')
    def test_contract_hold_counterexample_exposes_engine_problem(self):
        first=e.ret({'A':100,'B':100},{'A':200,'B':100},['A','B'])
        second=e.ret({'A':200,'B':100},{'A':100,'B':100},['A','B'])
        self.assertEqual((1+first)*(1+second)-1,.125)
        self.assertEqual((100+100)/(100+100)-1,0.)
        self.assertFalse(e.audit_weighting()['engine_changed'])
    def test_report_does_not_turn_fresh_signals_into_fresh_economics(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        e.write_json(self.root/'ledgers/momentum_m1_m2/STATUS.json',{'status':'ACTIVE','data_as_of':'2026-09-26'})
        eroot=self.root/'ledgers/momentum_m1_m2_economics'
        e.write_json(eroot/'ECONOMICS_STATUS.json',{'status':'ECONOMICS_ACTIVE','data_as_of':'2026-09-13','cost_status':'N_D'})
        e.write_json(eroot/'DELIVERY_STATUS.json',{'status':'BLOCKED_GAP_DISPOSITION_REQUIRED','gaps':[{'missing_closes':12}]})
        report=enrich(self.root,{'reference_data_date':'2026-09-26'})
        row=report['components']['momentum_m1_m2']
        self.assertEqual(row['freshness'],'FRESH');self.assertEqual(row['economic_freshness'],'STALE');self.assertEqual(row['collection_health_hint'],'AMBER_BLOCKED_DEPENDENCY')
        self.assertIn('momentum_m1_m2',report['warnings']['blocked_dependency_components'])
    def test_workflow_propagates_failure_after_diagnostic_publication(self):
        text=Path('.github/workflows/gate-btc-momentum-economics.yml').read_text()
        self.assertIn("steps.append.outcome != 'success'",text)
        self.assertIn('Publish source evidence and actual economic blockage',text)
        self.assertNotIn('NOOP_MISSING_FROZEN_PRICE_COVERAGE',text)
        self.assertIn('MOMENTUM_ORIGINAL_ECONOMIC_HISTORY_UNCHANGED',text)

if __name__=='__main__':unittest.main()
