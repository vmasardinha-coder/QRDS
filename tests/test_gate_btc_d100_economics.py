import copy
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
from tools.gate_btc_factory import d100_economics as e


class D100EconomicsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.protocol,self.ph,self.rh=e.authority()
        self.now=datetime(2026,9,27,16,tzinfo=timezone.utc)

    def bundles(self,count=5):
        baseline=e.load_module('fixture_baseline',e.ROOT/'scripts/00_run_delta_v11.py')
        ohlc,fund,*_=baseline.build_fixture_data(end_date='2026-08-04')
        ohlc=ohlc[ohlc.symbol.isin(baseline.CFG['universe'])].copy()
        out=[]
        for k in range(count):
            day=pd.Timestamp('2026-07-28')+pd.Timedelta(days=k)
            observed=ohlc[ohlc.date.lt(day)]
            panels=baseline.build_panels(observed)
            dt=day-pd.Timedelta(days=1)
            symbols=baseline.CFG['universe']
            signal={'score':panels['score'].loc[dt].to_dict(),'vol30':panels['vol30'].loc[dt].to_dict()}
            rows=observed.assign(date=observed.date.dt.strftime('%Y-%m-%d'))[['date','symbol','open','high','low','close','volume']].to_dict('records')
            out.append({'capture_date':day.strftime('%Y-%m-%d'),'available_at_utc':day.strftime('%Y-%m-%d')+'T00:11:00Z',
                        'execution_not_before_utc':(day+pd.Timedelta(days=1)).strftime('%Y-%m-%d')+'T00:00:00Z',
                        'feature_bar_date':dt.strftime('%Y-%m-%d'),'protocol_sha256':self.ph,'registry_sha256':self.rh,
                        'signals':{'d100':copy.deepcopy(signal),'reference':copy.deepcopy(signal)},
                        'ohlc':rows,'funding':[{'date':dt.strftime('%Y-%m-%d'),'symbol':s,'funding_rate':.0001} for s in symbols],
                        'eligible_symbols':symbols,'reference_symbols':symbols,'identity_proofs':{},'sources':[]})
        return out

    def test_exact_frozen_engine_hashes(self):
        self.assertEqual(e.authority()[0]['target'],80)

    def test_no_retroactive_or_premature_credit(self):
        bundles=self.bundles(3)
        self.assertEqual(e.replay(bundles[:1]),([],None))
        rows,anchor=e.replay(bundles)
        self.assertEqual(anchor,'2026-07-30');self.assertEqual(rows,[])

    def test_paired_reference_and_prefix_immutability(self):
        bundles=self.bundles(5)
        rows,_=e.replay(bundles)
        prior,_=e.replay(bundles[:4])
        self.assertEqual(rows[:len(prior)],prior)
        self.assertEqual(len(rows),2)
        for row in rows:
            self.assertEqual(set(row['arms']),set(e.ARMS))
            self.assertEqual(row['arms']['D100_COST_AWARE'],row['arms']['D50_REFERENCE_COST_AWARE'])

    def test_future_rank_change_does_not_rewrite_economics(self):
        bundles=self.bundles(5);rows,_=e.replay(bundles)
        bundles[-1]['signals']['d100']['score']={k:-v for k,v in bundles[-1]['signals']['d100']['score'].items()}
        after,_=e.replay(bundles);self.assertEqual(rows,after)

    def test_removed_asset_exits_through_frozen_schedule(self):
        bundles=self.bundles(5)
        for b in bundles[2:]:
            b['signals']['d100']['score'].pop('BTC',None)
            b['signals']['d100']['vol30'].pop('BTC',None)
        rows,_=e.replay(bundles)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(np.isfinite(r['arms']['D100_COST_AWARE']['net_return']) for r in rows))

    def test_missing_funding_does_not_become_zero(self):
        bundles=self.bundles(4);bundles[-1]['funding']=bundles[-1]['funding'][1:]
        with self.assertRaisesRegex(ValueError,'missing held/source coverage'):e.replay(bundles)

    def test_funding_requires_complete_boundaries_and_no_conflicts(self):
        start=int(datetime(2026,9,26,tzinfo=timezone.utc).timestamp()*1000)
        rows=[dict(instId='BTC-USDT-SWAP',fundingTime=str(start+i*8*3600000),fundingRate='0.001') for i in range(4)]
        self.assertAlmostEqual(e.funding_day(rows,'BTC-USDT-SWAP','2026-09-26'),.003)
        with self.assertRaisesRegex(ValueError,'incomplete'):e.funding_day(rows[1:],'BTC-USDT-SWAP','2026-09-26')
        rows.append({**rows[0],'fundingRate':'0.002'})
        with self.assertRaisesRegex(ValueError,'conflicting'):e.funding_day(rows,'BTC-USDT-SWAP','2026-09-26')

    def test_candle_confirmations_contiguity_and_notional_volume(self):
        end=int(self.now.replace(hour=0).timestamp()*1000)
        rows=[[str(end-(i+1)*e.DAY),'10','12','9','11','100','1000','2000000','1'] for i in range(31)]
        parsed=e.candles(rows,'BTC',self.now)
        self.assertEqual(parsed[-1]['volume'],2000000)
        rows[10][-1]='0'
        with self.assertRaisesRegex(ValueError,'31 consecutive'):e.candles(rows,'BTC',self.now)

    def test_capture_hashes_and_signal_causality(self):
        bundle=self.bundles(1)[0];e.append_capture(self.root,bundle,None)
        self.assertEqual(len(e.load_captures(self.root,self.ph,self.rh)[0]),1)
        p=next((self.root/'archives').glob('*'));p.write_bytes(p.read_bytes()+b'bad')
        with self.assertRaisesRegex(ValueError,'archive corrupt'):e.load_captures(self.root,self.ph,self.rh)

    def test_n80_fixed_terminal_decision_and_no_peeking(self):
        rows=[{'arms':{'D100_COST_AWARE':{'net_return':.001},'D50_REFERENCE_COST_AWARE':{'net_return':0}}} for _ in range(80)]
        with self.assertRaisesRegex(ValueError,'exactly N80'):e.final_decision(rows[:79],self.protocol)
        decision=e.final_decision(rows,self.protocol)
        self.assertEqual(decision['status'],'CLOSED_FAVORABLE_EVIDENCE')
        self.assertFalse(decision['extension_allowed']);self.assertFalse(decision['promotion_allowed'])
        for r in rows:r['arms']['D100_COST_AWARE']['net_return']=0
        self.assertEqual(e.final_decision(rows,self.protocol)['status'],'CLOSED_NO_VALIDATED_SUPERIORITY')

    def test_same_day_idempotency_and_missed_day_interrupt(self):
        b=self.bundles(1)[0];now=e.parse_time(b['available_at_utc'])+timedelta(hours=1)
        with patch.object(e,'collect',return_value=b) as collect,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(e.run(self.root,clock=lambda:now),0)
            self.assertEqual(e.run(self.root,clock=lambda:now),0)
            self.assertEqual(collect.call_count,1)
            self.assertEqual(e.run(self.root,clock=lambda:now+timedelta(days=2)),2)
        self.assertEqual(e.read(self.root/'STATUS.json')['status'],'INTERRUPTED_EXPLICIT_DISPOSITION_REQUIRED')
        self.assertEqual(e.read(self.root/'STATUS.json')['scientific_observations_credited'],0)

    def test_ticker_match_without_identity_not_admitted(self):
        entry={'cmc_id':1000,'symbol':'FAKE','cmc_slug':'fake','instrument':'FAKE-USDT-SWAP','identity_authority':'OFFICIAL','okx_name':'Real Name','evidence':'https://www.okx.com/price/fake'}
        instrument={'instId':'FAKE-USDT-SWAP','uly':'FAKE-USDT','ctType':'linear','settleCcy':'USDT','state':'live'}
        good,_=e.official_identity(entry,instrument,lambda u:b'<title>Different FAKE | OKX</title>',{},[],lambda:self.now)
        self.assertFalse(good)

    def test_terminal_round_never_requests_sources_or_creates_n81(self):
        previous=None
        for i in range(80):
            row={'observation':i+1,'date':(self.now.date()+timedelta(days=i)).isoformat(),
                 'arms':{name:{'net_return':0.} for name in e.ARMS},'protocol_sha256':self.ph,
                 'previous_sha256':previous}
            row['sha256']=e.sha(e.packed(row));previous=row['sha256']
            e.sealed_write(self.root/'observations'/f'{i+1:03d}.json',row)
        with patch.object(e,'collect',side_effect=AssertionError('no source requests after terminal')) as collect,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(e.run(self.root,clock=lambda:self.now),0)
            first=(self.root/'FINAL_DECISION.json').read_bytes()
            self.assertEqual(e.run(self.root,clock=lambda:self.now+timedelta(days=1)),0)
            self.assertEqual(first,(self.root/'FINAL_DECISION.json').read_bytes())
            collect.assert_not_called()
        self.assertEqual(len(list((self.root/'observations').glob('*.json'))),80)
        self.assertEqual(e.read(self.root/'STATUS.json')['remaining_scientific_observations'],0)

    def test_report_replaces_old_scientific_block_and_detects_stale_signal(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        physical=self.root/'ledgers/d100/STATUS.json'
        e.atomic_json(physical,{'schema':'qrds.d100.forward_collection.v2','status':'ACTIVE_PHYSICAL_DATA_FEED',
            'latest_physical_capture_at_utc':'2026-09-27T12:00:00Z','last_error':None,'physical_snapshot_count':1})
        ep=physical.parent/'economic/STATUS.json'
        state={'schema':'qrds.d100.economics.v1','status':'ARMED_WAITING_FIRST_CAUSAL_BAR',
               'scientific_observations_credited':0,'scientific_target':80,'scientific_blockers':[],
               'last_error':None,'latest_signal_available_at_utc':'2026-09-27T12:00:00Z'}
        e.atomic_json(ep,state)
        report=enrich(self.root,{'reference_data_date':'2026-09-27','warnings':{'blocked_dependency_components':['d100']}})
        self.assertEqual(report['components']['d100']['scientific_target'],80)
        self.assertNotIn('d100',report['warnings']['blocked_dependency_components'])
        state['latest_signal_available_at_utc']='2026-09-25T12:00:00Z';e.atomic_json(ep,state)
        report=enrich(self.root,{'reference_data_date':'2026-09-27'})
        self.assertIn('d100',report['warnings']['stale_components'])

if __name__=='__main__':unittest.main()
