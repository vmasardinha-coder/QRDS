import copy,importlib.util,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd
from tools import gate_btc_qos_covered_delivery as q

spec=importlib.util.spec_from_file_location('qos_fixtures',Path(__file__).with_name('test_gate_btc_qos_prospective_three_track.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)


class CoveredDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'ledger';self.root.mkdir()
        self.config=q.core.load(q.APPROVAL)
        self.state=fixtures.state();old=self.root/'cycles/2026-08-31'
        q.core.write(old/'SIGNAL_STATE.json',self.state)
        q.core.write(old/'STATUS.json',{'status':'WAITING_CYCLE_COMPLETION'})
        self.config['original_cycle_sha256']={str(p.relative_to(old)):q.sha(p.read_bytes()) for p in old.rglob('*.json')}
        self.day='2026-09-30';self.at=datetime(2026,10,1,8,tzinfo=timezone.utc)

    def master(self,missing=()):
        return pd.DataFrame([{'date':self.day,'symbol':a,'source':'S','close_usd':100.0}
                             for a in ('AAA','BBB','CCC') if a not in missing])

    def test_closure_preserves_original_bytes_and_is_idempotent(self):
        old=self.root/'cycles/2026-08-31';before={p:p.read_bytes() for p in old.rglob('*.json')}
        q.disposition(self.root,self.config);q.disposition(self.root,self.config)
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(q.core.load(old/'BLOCKED.json')['economic_credit'],0)

    def test_changed_original_blocks_disposition(self):
        (self.root/'cycles/2026-08-31/STATUS.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'INTERRUPTED_CYCLE_CHANGED'):q.disposition(self.root,self.config)

    def test_wait_does_not_request_or_count_source_work(self):
        need,s=q.plan(self.root,self.config,datetime(2026,9,28,tzinfo=timezone.utc))
        self.assertFalse(need);self.assertEqual(s['status'],'WAITING_NEXT_APPROVED_MONTH_END')
        self.assertFalse((self.root/'retry_budget.json').exists())

    def test_bound_current_day_retry_attempts(self):
        for _ in range(6):self.assertTrue(q.plan(self.root,self.config,self.at)[0])
        need,s=q.plan(self.root,self.config,self.at)
        self.assertFalse(need);self.assertEqual(s['status'],'BLOCKED_DAILY_RETRY_BUDGET')

    def test_removed_selected_asset_is_requested_from_same_locked_source(self):
        calls=[]
        def loader(a):calls.append(a);return self.master()
        frame=q.cover(self.state,self.master(['AAA']),self.day,self.root/'evidence','zip',self.at,{'S':loader})
        self.assertEqual(calls,['AAA']);self.assertEqual(set(frame.symbol),{'AAA','BBB','CCC'})

    def test_missing_selected_does_not_commit_a_successful_price_manifest(self):
        with self.assertRaisesRegex(q.MissingLockedSelectedPrices,'MISSING_LOCKED_SELECTED_PRICES:AAA') as captured:
            q.cover(self.state,self.master(['AAA']),self.day,self.root/'evidence','zip',self.at,{})
        self.assertEqual(captured.exception.selected,['AAA'])
        self.assertEqual(captured.exception.source_locks,{'AAA':'S'})
        self.assertEqual(captured.exception.cutoff,self.day)
        self.assertFalse(list((self.root/'evidence').rglob('PRICES.json')))
        self.assertTrue(list((self.root/'evidence/failed_attempts').rglob('*.gz')))

    def test_source_substitution_cannot_fill_missing_selected_price(self):
        wrong=self.master();wrong['source']='OTHER'
        with self.assertRaisesRegex(ValueError,'MISSING_LOCKED_SELECTED'):
            q.cover(self.state,self.master(['AAA']),self.day,self.root/'evidence','zip',self.at,{'S':lambda a:wrong})

    def test_unresolved_control_stays_in_frozen_denominator(self):
        s=copy.deepcopy(self.state);s['candidate_symbols'].append('DDD');s['candidate_source_lock']['DDD']='S';s['candidate_count']=4;s['state_sha256']=q.core.sharow(s)
        q.cover(s,self.master(),self.day,self.root/'evidence','zip',self.at,{})
        m=q.core.load(next((self.root/'evidence').rglob('PRICES.json')))
        self.assertEqual(m['candidate_count'],4);self.assertEqual(m['missing_candidates'],['DDD'])

    def test_cached_evidence_does_not_refetch_and_detects_corruption(self):
        q.cover(self.state,self.master(),self.day,self.root/'evidence','zip',self.at,{})
        q.cover(self.state,self.master(['AAA']),self.day,self.root/'evidence','otherzip',self.at,{})
        p=next((self.root/'evidence').rglob('PRICES.json'));m=q.core.load(p);m['quotes'][0]['close_usd']=999;q.core.write(p,m)
        with self.assertRaisesRegex(ValueError,'PRICE_MANIFEST_CORRUPT'):
            q.cover(self.state,self.master(),self.day,self.root/'evidence','zip',self.at,{})

    def test_next_month_signal_can_start_without_touching_old_cycle(self):
        q.disposition(self.root,self.config)
        before={p:p.read_bytes() for p in (self.root/'cycles/2026-08-31').rglob('*.json')}
        z=Path(self.tmp.name)/'source.zip';fixtures.write_v2a(z,self.day,self.master())
        s=q.process(self.root,self.config,z,'newrun',self.at,{})
        self.assertEqual(s['status'],'ACTIVE_PROSPECTIVE_THREE_TRACK')
        self.assertEqual(s['result_ledger_rows'],0)
        self.assertTrue((self.root/'cycles/2026-09-30/path/snapshots/2026-09-30.json').exists())
        q.process(self.root,self.config,z,'rerun',self.at,{})
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(len(list((self.root/'cycles/2026-09-30/path/snapshots').glob('*.json'))),1)

    def test_failed_coverage_rolls_back_new_scientific_cycle(self):
        q.disposition(self.root,self.config)
        z=Path(self.tmp.name)/'source.zip'
        master=pd.concat([self.master(['AAA']),pd.DataFrame([{'date':'2026-09-29','symbol':'AAA','source':'S','close_usd':100.0}])])
        fixtures.write_v2a(z,self.day,master)
        with self.assertRaisesRegex(ValueError,'MISSING_LOCKED_SELECTED'):
            q.process(self.root,self.config,z,'run',self.at,{})
        self.assertFalse((self.root/'cycles/2026-09-30').exists())
        self.assertFalse((self.root/'RESULT_LEDGER.json').exists())

    def test_stale_source_cannot_backfill(self):
        q.disposition(self.root,self.config)
        z=Path(self.tmp.name)/'source.zip';fixtures.write_v2a(z,'2026-09-29',self.master())
        with self.assertRaisesRegex(ValueError,'UPSTREAM_NOT_CURRENT'):
            q.process(self.root,self.config,z,'run',self.at,{})

    def test_report_shows_closed_legacy_and_calendar_wait_then_stale(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        runtime=Path(self.tmp.name)/'runtime';target=runtime/'ledgers/qos_three_track'
        s={**q.SAFE,'schema':'gate_btc.qos_covered_delivery.v1','status':'WAITING_NEXT_APPROVED_MONTH_END',
           'next_signal_date':'2026-09-30','latest_snapshot_date':'2026-09-08','interrupted_cycle_economic_credit':0}
        q.core.write(target/'STATUS.json',s)
        before=enrich(runtime,{},as_of_utc=datetime(2026,9,29,tzinfo=timezone.utc))['components']['qos_three_track']
        after=enrich(runtime,{},as_of_utc=datetime(2026,10,1,tzinfo=timezone.utc))['components']['qos_three_track']
        self.assertEqual(before['freshness'],'CURRENT_CALENDAR_GATED')
        self.assertEqual(after['freshness'],'STALE')
        self.assertEqual(after['collection_health_hint'],'AMBER_BLOCKED_DEPENDENCY')


if __name__=='__main__':unittest.main()
