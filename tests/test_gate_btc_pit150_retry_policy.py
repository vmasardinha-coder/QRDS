import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from tools.gate_btc_pit150_retry_policy import decision, load_policy, annotate_followup
from tools.gate_btc_v2a_failure_diagnostic import build_diagnostic
from tools.gate_btc_shadow_executive import build

ROOT = Path(__file__).resolve().parents[1]

class RetryPolicyTests(unittest.TestCase):
    def test_old_cutoffs_core_and_changed_identity_never_deferred(self):
        for sym, identity, day in [('BUIDL', 'blackrock-usd-institutional-digital-liquidity-fund', '2026-10-21'),
                                   ('BUIDL', 'different-asset', '2026-10-22'),
                                   ('BTC', 'bitcoin', '2026-10-22'), ('ETH', 'ethereum', '2026-10-22')]:
            self.assertIsNone(decision(sym, identity, day))

    def test_maturity_and_bounded_weekly_retry(self):
        self.assertEqual(decision('APXUSD', 'apxusd', '2026-10-22')['next_retry_cutoff'], '2026-11-05')
        self.assertIsNone(decision('APXUSD', 'apxusd', '2026-11-05'))
        self.assertEqual(decision('APXUSD', 'apxusd', '2026-11-06')['next_retry_cutoff'], '2026-11-12')
        self.assertIsNone(decision('APXUSD', 'apxusd', '2026-11-12'))

    def test_all_known_cases_have_explicit_disposition(self):
        cases = load_policy()['cases']
        self.assertEqual(len(cases), 20)
        for c in cases:
            d = decision(c['symbol'], c['coin_id'], c.get('effective_cutoff', '2026-10-22'))
            self.assertIsNotNone(d)
            self.assertFalse(d['coverage_repaired'])

    def test_collector_suppresses_requests_and_keeps_denominator_gap(self):
        spec = importlib.util.spec_from_file_location('retry_collector', ROOT/'migration/canonical/v2a/scripts/00_run_all_v2a.py')
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        universe = pd.DataFrame([{'symbol':'BUIDL', 'id':'blackrock-usd-institutional-digital-liquidity-fund', 'standard_ticker':True, 'is_stable':False, 'is_blocked':False}])
        def loader(session, symbol):
            if symbol == 'BUIDL': raise AssertionError('deferred coin must not request a source')
            return pd.DataFrame({'date': pd.date_range(end='2026-10-22', periods=200), 'symbol':symbol, 'close_usd':100., 'volume_usd':10., 'source':'cdd'})
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GATE_BTC_DATA_CUTOFF':'2026-10-22'}), patch.object(m,'OUT',Path(tmp)), patch.object(m,'DATA_PROCESSED',Path(tmp)), patch.object(m.time,'sleep'), patch.object(m,'tqdm',side_effect=lambda x,**kw:x), patch.object(m,'fetch_cdd_symbol',side_effect=loader) as calls:
            master, failed = m.fetch_candles_for_universe(None, universe)
            self.assertEqual([c.args[1] for c in calls.call_args_list], ['BTC','ETH'])
            self.assertEqual(set(master.symbol), {'BTC','ETH'})
            self.assertEqual(failed.symbol.tolist(), ['BUIDL'])
            report = build_diagnostic(universe.to_dict('records'), failed.to_dict('records'), {'data_as_of':'2026-10-22','attempted_symbols':3,'loaded_symbols':2,'failed_symbols':1})
            self.assertEqual(report['action_counts']['OPERATIONALLY_DEFERRED'],1)
            self.assertFalse(report['rows'][0]['source_attempts_available'])
            tampered = failed.to_dict('records'); tampered[0]['reason'] = tampered[0]['reason'].replace('2026-10-22','2026-10-23')
            with self.assertRaises(RuntimeError): build_diagnostic(universe.to_dict('records'),tampered,{'data_as_of':'2026-10-22','attempted_symbols':3,'loaded_symbols':2,'failed_symbols':1})

    def test_followup_preserves_gap_and_exposes_wait(self):
        p = {'data_as_of':'2026-10-22','legacy_loaded_symbols':133,'pit150_denominator_preserved':150,'assets':[{'symbol':'APXUSD','pit150_identity':'apxusd','legacy_gap_resolved':False}]}
        result = annotate_followup(p)
        self.assertEqual(result['deferred_case_count'],1)
        self.assertFalse(result['assets'][0]['operational_repair_required'])
        self.assertFalse(result['assets'][0]['legacy_gap_resolved'])
        self.assertEqual(result['legacy_loaded_symbols'],133)

    def test_c4_reference_freeze_does_not_stop_current_proxy(self):
        report = build({'components':{'bull_replay_live_shadow':{'session':'2026-10-22','proxy_return':-0.01}}}, '2026-10-22')
        block = next(b['content'] for b in report['blocks'] if b['block_id']=='04_proxy_real')
        self.assertTrue(block['c4_reference']['comparison_updates_enabled'])
        self.assertFalse(block['c4_reference']['reference_is_current_daily_valuation'])
        self.assertEqual(block['bull_replay_live_shadow']['session'], '2026-10-22')
        self.assertEqual(block['c4_reference']['reference_balance_brl'],200000)

if __name__ == '__main__': unittest.main()


