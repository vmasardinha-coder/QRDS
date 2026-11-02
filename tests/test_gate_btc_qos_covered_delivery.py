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

    def test_retry_opportunities_remain_available_after_early_attempts(self):
        from datetime import timedelta
        for hour in range(8,14):
            now=self.at+timedelta(hours=hour-8)
            self.assertTrue(q.plan(self.root,self.config,now)[0])
            need,s=q.plan(self.root,self.config,now)
            self.assertFalse(need)
            self.assertEqual(s['status'],'WAITING_NEXT_HOURLY_RETRY')
        late=self.at+timedelta(hours=14)
        self.assertTrue(q.plan(self.root,self.config,late)[0])
        self.assertEqual(q.core.load(self.root/'retry_budget.json')['attempts'],7)

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

    def test_expired_selected_gap_archives_original_cycle_once(self):
        q.disposition(self.root,self.config)
        cycle=self.root/'cycles/2026-09-30'
        state=fixtures.state()
        state['signal_date']='2026-09-30'
        state['state_sha256']=q.core.sharow(state)
        q.core.write(cycle/'SIGNAL_STATE.json',state)
        q.core.write(cycle/'STATUS.json',{'status':'WAITING_CYCLE_COMPLETION'})
        row={'snapshot_date':'2026-10-04','signal_date':'2026-09-30'}
        row['row_sha256']=q.core.sharow(row)
        q.core.write(cycle/'path/snapshots/2026-10-04.json',row)
        q.core.write(self.root/'STATUS.json',{'status':'FAILED_QOS_DELIVERY',
            'latest_snapshot_date':'2026-10-04','missing_selected_cutoff':'2026-10-05'})
        before={p:p.read_bytes() for p in cycle.rglob('*') if p.is_file()}
        now=datetime(2026,10,7,8,tzinfo=timezone.utc)
        need,status=q.plan(self.root,self.config,now)
        self.assertFalse(need)
        self.assertEqual(status['status'],'WAITING_NEXT_APPROVED_MONTH_END')
        self.assertEqual(status['next_signal_date'],'2026-10-31')
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        marker=(cycle/'BLOCKED.json').read_bytes()
        q.plan(self.root,self.config,now)
        self.assertEqual(marker,(cycle/'BLOCKED.json').read_bytes())
        self.assertEqual(q.core.load(cycle/'BLOCKED.json')['economic_credit'],0)

    def test_source_epoch_remaps_only_prequalified_symbols_after_signal_date(self):
        from unittest.mock import patch
        state=fixtures.state()
        state['candidate_source_lock']={'AR':'cdd','LINK':'cdd','AAA':'cdd'}
        state['candidate_symbols']=['AR','LINK','AAA']
        state['state_sha256']=q.core.sharow(state)
        with patch.object(q,'ORIGINAL_CAPTURE',return_value=state):
            before=q.epoch_capture(None,None,'2026-09-30','source')
            after=q.epoch_capture(None,None,'2026-10-31','source')
        self.assertEqual(before['candidate_source_lock']['AR'],'cdd')
        self.assertEqual(after['candidate_source_lock']['AR'],'binance_spot_daily_archive')
        self.assertEqual(after['candidate_source_lock']['LINK'],'binance_spot_daily_archive')
        self.assertEqual(after['candidate_source_lock']['AAA'],'cdd')
        self.assertEqual(state['candidate_source_lock']['AR'],'cdd')
        self.assertEqual(after['state_sha256'],q.core.sharow(after))

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

    def test_calendar_keeps_first_authority_and_advances_after_captured_october_signal(self):
        q.core.write(self.root/'cycles/2026-10-31/SIGNAL_STATE.json',{'signal_date':'2026-10-31'})
        out=q.status(self.root,self.config,'ACTIVE_PROSPECTIVE_THREE_TRACK',datetime(2026,11,1,tzinfo=timezone.utc))
        self.assertEqual(out['approved_first_signal_date'],'2026-09-30')
        self.assertEqual(out['latest_captured_signal_date'],'2026-10-31')
        self.assertEqual(out['next_signal_date'],'2026-11-30')
        self.assertEqual(self.config['next_signal_date'],'2026-09-30')

    def test_calendar_does_not_skip_missing_signal_based_on_wall_clock(self):
        q.core.write(self.root/'cycles/2026-09-30/SIGNAL_STATE.json',{'signal_date':'2026-09-30'})
        out=q.status(self.root,self.config,'FAILED_QOS_DELIVERY',datetime(2026,11,1,tzinfo=timezone.utc))
        self.assertEqual(out['next_signal_date'],'2026-10-31')
        self.assertEqual(out['orders_generated'],0)
        self.assertFalse(out['backfill_performed'])

    def test_calendar_without_approved_capture_keeps_first_signal_date(self):
        out=q.signal_calendar(self.root,self.config)
        self.assertEqual(out['next_signal_date'],'2026-09-30')
        self.assertIsNone(out['latest_captured_signal_date'])

    def test_calendar_handles_leap_month_and_year_rollover(self):
        for captured,wanted in [('2024-01-31','2024-02-29'),('2026-12-31','2027-01-31')]:
            with self.subTest(captured=captured),tempfile.TemporaryDirectory() as td:
                root=Path(td);config={**self.config,'next_signal_date':captured}
                q.core.write(root/'cycles'/captured/'SIGNAL_STATE.json',{'signal_date':captured})
                self.assertEqual(q.signal_calendar(root,config)['next_signal_date'],wanted)

    def test_explicit_approved_wait_override_remains_supported(self):
        out=q.status(self.root,self.config,'WAITING_NEXT_APPROVED_MONTH_END',self.at,
                     next_signal_date='2026-10-31')
        self.assertEqual(out['next_signal_date'],'2026-10-31')
        self.assertEqual(out['approved_first_signal_date'],'2026-09-30')

    def test_delivered_day_repairs_only_metadata_without_refetch_or_freshening(self):
        q.disposition(self.root,self.config)
        cycle=self.root/'cycles/2026-10-31'
        q.core.write(cycle/'SIGNAL_STATE.json',{'signal_date':'2026-10-31'})
        q.core.write(cycle/'path/snapshots/2026-10-31.json',{'sealed_test_row':True})
        old={**q.SAFE,'status':'ACTIVE_PROSPECTIVE_THREE_TRACK','latest_snapshot_date':'2026-10-31',
             'updated_at_utc':'2026-11-01T08:12:50Z','next_signal_date':'2026-09-30',
             'result_ledger_rows':0,'custom_evidence':'preserve'}
        q.core.write(self.root/'STATUS.json',old)
        protected={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.name!='STATUS.json'}
        need,out=q.plan(self.root,self.config,datetime(2026,11,1,23,tzinfo=timezone.utc))
        self.assertFalse(need)
        self.assertEqual(out['next_signal_date'],'2026-11-30')
        for key in old:
            if key!='next_signal_date':self.assertEqual(out[key],old[key])
        self.assertEqual(protected,{p:p.read_bytes() for p in protected})
        self.assertFalse((self.root/'retry_budget.json').exists())
        saved=(self.root/'STATUS.json').read_bytes()
        self.assertFalse(q.plan(self.root,self.config,datetime(2026,11,1,23,tzinfo=timezone.utc))[0])
        self.assertEqual(saved,(self.root/'STATUS.json').read_bytes())


if __name__=='__main__':unittest.main()
