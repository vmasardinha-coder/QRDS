import copy
import json
import tempfile
import unittest
from argparse import Namespace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from tools import gate_btc_momentum_hold_epoch as h


class HoldEpochTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = h.load_json(h.APPROVAL)
        self.contract = h.load_json(h.CONTRACT)
        for name in self.config['legacy_seals']:
            (self.root/name).write_bytes(b'{"old":true}\n')
            self.config['legacy_seals'][name] = h.digest((self.root/name).read_bytes())
        self.assets = ['A'+str(i) for i in range(10)]
        self.prices = {a: 100.0 for a in self.assets + ['BTC', 'NEW']}
        self.evidence = {'snapshot_sha256': 'signal', 'price_manifest_sha256': 'prices'}

    def snapshot(self, day=0, assets=None):
        assets = assets or self.assets
        return {'cutoff': (date(2026,9,28)+timedelta(days=day)).isoformat(),
                **{block: {'rows': [{'asset':a, rank:i+1} for i,a in enumerate(assets)]}
                   for block,rank in h.STRATS.values()}}

    def advance(self, ledger=None, day=0, prices=None, assets=None):
        snap = self.snapshot(day, assets)
        at = datetime.combine(date.fromisoformat(snap['cutoff'])+timedelta(days=1),
                              datetime.min.time(), tzinfo=timezone.utc)
        return h.advance(ledger, snap, prices or self.prices, self.config, self.contract, self.evidence, at)

    def test_independent_activation_nav_one_zero_return_observations(self):
        ledger,_ = self.advance()
        self.assertEqual(ledger['state']['return_observations'],0)
        self.assertEqual(ledger['state']['nav'],{'M1_TOP10':1.0,'M2_TOP10':1.0})
        self.assertIsNone(ledger['rows'][0]['daily_return_gross']['M1_TOP10'])
        self.assertIsNone(ledger['rows'][0]['net_return'])

    def test_round_trip_prices_hold_returns_zero_not_daily_rebalanced_gain(self):
        ledger,_ = self.advance()
        original = copy.deepcopy(ledger['state']['quantities'])
        ledger,_ = self.advance(ledger,1,{**self.prices,'A0':200.0})
        self.assertAlmostEqual(ledger['state']['nav']['M1_TOP10'],1.1)
        ledger,_ = self.advance(ledger,2)
        self.assertAlmostEqual(ledger['state']['nav']['M1_TOP10'],1.0)
        self.assertEqual(ledger['state']['quantities'],original)

    def test_rebalance_on_seventh_return_after_marking_old_positions(self):
        ledger,_ = self.advance()
        current = ['NEW'] + self.assets[1:]
        for day in range(1,7):
            ledger,_ = self.advance(ledger,day,assets=current)
            self.assertIn('A0',ledger['state']['holdings']['M1_TOP10'])
        ledger,_ = self.advance(ledger,7,{**self.prices,'A0':200.0},current)
        self.assertEqual(ledger['rows'][-1]['event'],'REBALANCE')
        self.assertAlmostEqual(ledger['state']['nav']['M1_TOP10'],1.1)
        self.assertEqual(ledger['state']['closes_since_rebalance'],0)
        self.assertNotIn('A0',ledger['state']['holdings']['M1_TOP10'])
        self.assertAlmostEqual(ledger['state']['quantities']['M1_TOP10']['NEW']*100,0.11)

    def test_btc_is_fixed_quantity_buy_and_hold(self):
        ledger,_ = self.advance()
        ledger,_ = self.advance(ledger,1,{**self.prices,'BTC':200})
        self.assertEqual(ledger['state']['btc_nav'],2)
        ledger,_ = self.advance(ledger,2)
        self.assertEqual(ledger['state']['btc_nav'],1)

    def test_duplicate_does_not_append_or_mutate(self):
        ledger,_ = self.advance()
        before = copy.deepcopy(ledger)
        again, changed = self.advance(ledger)
        self.assertFalse(changed)
        self.assertEqual(again,before)

    def test_new_gap_blocks_without_changing_input_state(self):
        ledger,_ = self.advance()
        before = copy.deepcopy(ledger)
        with self.assertRaisesRegex(ValueError,'NO_SILENT_BRIDGE'):
            self.advance(ledger,2)
        self.assertEqual(ledger,before)

    def test_missing_held_price_is_not_dropped_or_zero_filled(self):
        ledger,_ = self.advance()
        px = dict(self.prices);del px['A0']
        with self.assertRaises(KeyError):
            self.advance(ledger,1,px)

    def test_invalid_price_blocks(self):
        with self.assertRaisesRegex(ValueError,'INVALID_PRICE'):
            self.advance(prices={**self.prices,'A0':float('nan')})

    def test_preapproval_cutoff_cannot_initialize(self):
        with self.assertRaisesRegex(ValueError,'PRE_APPROVAL'):
            self.advance(day=-1)

    def test_history_and_counter_authority_fail_closed(self):
        ledger,_ = self.advance()
        ledger['state']['return_observations']=30
        with self.assertRaisesRegex(ValueError,'STATE_HISTORY'):
            self.advance(ledger,1)

    def test_setup_preserves_legacy_and_is_idempotent(self):
        before={p:p.read_bytes() for p in self.root.iterdir()}
        epoch=h.setup(self.root,self.config,self.contract)
        self.assertEqual(epoch,h.setup(self.root,self.config,self.contract))
        self.assertEqual(before,{p:p.read_bytes() for p in before})
        self.assertEqual(h.load_json(self.root/'INTERRUPTED_EPOCH.json')['pnl_transferred'],0)
        changed=copy.deepcopy(self.config);changed['approved_at_utc']='2026-09-29T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'IMMUTABLE'):
            h.setup(self.root,changed,self.contract)

    def test_changed_legacy_seal_blocks_setup(self):
        (self.root/'STATE.json').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'LEGACY_SEAL'):
            h.setup(self.root,self.config,self.contract)

    def test_waiting_does_not_fetch_prices_or_create_return_ledger(self):
        config_path=self.root/'config.json';h.save(config_path,self.config)
        args=Namespace(ledger_dir=self.root,snapshot=self.root/'unavailable.json',output_zip=self.root/'px.zip',phase='prepare')
        with patch.object(h,'APPROVAL',config_path),patch('tools.gate_btc_momentum_required_prices.collect') as collect:
            status=h.run(args,clock=lambda:datetime(2026,9,28,8,tzinfo=timezone.utc))
            collect.assert_not_called()
        self.assertEqual(status['status'],'WAITING_FIRST_POST_APPROVAL_CLOSE')
        self.assertEqual(status['return_observations'],0)
        self.assertFalse((self.root/'epochs/hold_20260928/LEDGER.json').exists())

    def test_report_uses_new_epoch_instead_of_legacy_pnl(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        eroot=self.root/'ledgers/momentum_m1_m2_economics'
        h.save(self.root/'ledgers/momentum_m1_m2/STATUS.json',{'status':'ACTIVE','data_as_of':'2026-09-27'})
        h.save(eroot/'ACTIVE_EPOCH.json',{**h.SAFETY,'epoch_id':'hold_20260928','relative_path':'epochs/hold_20260928'})
        h.save(eroot/'ECONOMICS_STATUS.json',{'status':'LEGACY','data_as_of':'2026-09-13','nav':{'M1_TOP10':99}})
        h.report(eroot/'epochs/hold_20260928',self.config,'WAITING_FIRST_POST_APPROVAL_CLOSE')
        result=enrich(self.root,{'reference_data_date':'2026-09-27'},as_of_utc=datetime(2026,9,28,tzinfo=timezone.utc))['components']['momentum_m1_m2']
        self.assertEqual(result['economic_status'],'WAITING_FIRST_POST_APPROVAL_CLOSE')
        self.assertIsNone(result['economic_nav'])
        self.assertEqual(result['return_observations'],0)
        self.assertEqual(result['economic_freshness'],'CURRENT_CALENDAR_GATED')
        expired=enrich(self.root,{'reference_data_date':'2026-09-27'},as_of_utc=datetime(2026,9,29,tzinfo=timezone.utc))['components']['momentum_m1_m2']
        self.assertEqual(expired['economic_status'],'FAILED_MISSING_FIRST_ECONOMIC_CLOSE')
        self.assertEqual(expired['collection_health_hint'],'RED_FAILED_DELIVERY')

    def test_full_capture_append_retry_and_corruption_rejection(self):
        import pandas as pd
        from tools import gate_btc_momentum_required_prices as p
        original_collect=p.collect
        config_path=self.root/'config.json';h.save(config_path,self.config)
        snap_path=self.root/'snapshot.json';h.save(snap_path,self.snapshot())
        args=Namespace(ledger_dir=self.root,snapshot=snap_path,output_zip=self.root/'px.zip',phase='prepare')
        clock=lambda:datetime(2026,9,29,4,tzinfo=timezone.utc)
        def loader(session,symbol):
            return pd.DataFrame([{'date':'2026-09-28','symbol':symbol,'close_usd':100.0}])
        def collect(*args,**kwargs):
            return original_collect(*args,**kwargs,loaders=[('fixture',loader)])
        before={n:(self.root/n).read_bytes() for n in self.config['legacy_seals']}
        with patch.object(h,'APPROVAL',config_path),patch.object(p,'collect',collect):
            self.assertEqual(h.run(args,clock)['price_count'],11)
            args.phase='append';first=h.run(args,clock)
            self.assertEqual(first['economic_rows_appended'],1)
            self.assertEqual(first['return_observations'],0)
            epoch=self.root/'epochs/hold_20260928'
            raw=(epoch/'LEDGER.json').read_bytes()
            (epoch/'ECONOMICS_STATUS.json').unlink()
            self.assertTrue(h.run(args,clock)['idempotent'])
            self.assertEqual((epoch/'LEDGER.json').read_bytes(),raw)
            self.assertEqual((epoch/'signals/2026-09-28.json').read_bytes(),snap_path.read_bytes())
            (epoch/'source_prices/2026-09-28/required_prices.zip').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError,'SOURCE_ARCHIVE_CORRUPT'):
                h.run(args,clock)
        self.assertEqual(before,{n:(self.root/n).read_bytes() for n in before})

    def test_missing_current_signal_after_first_close_is_failure_not_wait(self):
        config_path=self.root/'config.json';h.save(config_path,self.config)
        snap_path=self.root/'snapshot.json';h.save(snap_path,self.snapshot(-1))
        args=Namespace(ledger_dir=self.root,snapshot=snap_path,output_zip=self.root/'px.zip',phase='prepare')
        with patch.object(h,'APPROVAL',config_path):
            with self.assertRaisesRegex(ValueError,'CURRENT_MOMENTUM_SIGNAL_MISSING'):
                h.run(args,clock=lambda:datetime(2026,9,29,4,tzinfo=timezone.utc))


if __name__ == '__main__':
    unittest.main()
