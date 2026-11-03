import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from tools.gate_btc_pit150_retry_policy import decision, annotate_followup, load_policy

ROOT = Path(__file__).resolve().parents[1]


def collector():
    spec = importlib.util.spec_from_file_location(
        'spcxb_collector', ROOT/'migration/canonical/v2a/scripts/00_run_all_v2a.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SpcxbMaturityTests(unittest.TestCase):
    def test_exact_identity_future_boundary_and_historical_noninterference(self):
        identity = 'spacex-bstocks-tokenized-stock'
        self.assertIsNone(decision('SPCXB', identity, '2026-11-02'))
        self.assertIsNone(decision('SPCXB', 'different-wrapper', '2026-11-03'))
        d = decision('SPCXB', identity, '2026-11-03')
        self.assertEqual(d['disposition'], 'WAIT_HISTORY')
        self.assertEqual(d['next_retry_cutoff'], '2026-12-29')
        self.assertEqual(d['source_requests'], 0)
        self.assertFalse(d['coverage_repaired'])
        self.assertFalse(d['denominator_changed'])

    def test_due_date_runs_full_qa_not_automatic_admission(self):
        args = ('SPCXB', 'spacex-bstocks-tokenized-stock')
        self.assertIsNone(decision(*args, '2026-12-29'))
        self.assertEqual(decision(*args, '2026-12-30')['next_retry_cutoff'], '2027-01-05')
        self.assertIsNone(decision(*args, '2027-01-05'))
        self.assertEqual(load_policy()['history_required_rows'], 200)
        self.assertEqual(load_policy()['legacy_denominator'], 150)

    def test_collector_does_not_request_any_source_for_deferred_identity(self):
        m = collector()
        universe = pd.DataFrame([dict(symbol='SPCXB', id='spacex-bstocks-tokenized-stock',
                                     standard_ticker=True, is_stable=False, is_blocked=False)])
        def source(session, symbol):
            self.assertIn(symbol, ('BTC', 'ETH'))
            return pd.DataFrame(dict(date=pd.date_range(end='2026-11-03', periods=200),
                                     symbol=symbol, close_usd=100., volume_usd=10., source='cdd'))
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GATE_BTC_DATA_CUTOFF':'2026-11-03'}), \
             patch.object(m,'OUT',Path(tmp)), patch.object(m,'DATA_PROCESSED',Path(tmp)), \
             patch.object(m.time,'sleep'), patch.object(m,'tqdm',side_effect=lambda x,**kw:x), \
             patch.object(m,'fetch_cdd_symbol',side_effect=source) as first, \
             patch.object(m,'fetch_binance_klines',side_effect=AssertionError('unexpected Binance request')), \
             patch.object(m,'fetch_okx_candles',side_effect=AssertionError('unexpected OKX request')):
            master, failures = m.fetch_candles_for_universe(None, universe)
        self.assertEqual([c.args[1] for c in first.call_args_list], ['BTC','ETH'])
        self.assertEqual(set(master.symbol), {'BTC','ETH'})
        d = json.loads(failures.iloc[0]['reason'].split(':',1)[1])
        self.assertEqual(d['symbol'], 'SPCXB')
        self.assertEqual(d['source_requests'], 0)

    def test_followup_preserves_unresolved_coverage(self):
        p = dict(data_as_of='2026-11-03', legacy_loaded_symbols=131,
                 pit150_denominator_preserved=150,
                 assets=[dict(symbol='SPCXB',pit150_identity='spacex-bstocks-tokenized-stock',legacy_gap_resolved=False)])
        out = annotate_followup(p)
        self.assertEqual(out['legacy_loaded_symbols'],131)
        self.assertEqual(out['pit150_denominator_preserved'],150)
        self.assertFalse(out['assets'][0]['operational_repair_required'])
        self.assertFalse(out['assets'][0]['legacy_gap_resolved'])

    def test_live_bar_cannot_complete_200_rows(self):
        m = collector()
        frame = pd.DataFrame(dict(date=pd.date_range(end='2026-11-04',periods=200),symbol='NEW'))
        with patch.dict(os.environ, {'GATE_BTC_DATA_CUTOFF':'2026-11-03'}):
            bounded = m.requested_cutoff_history(frame)
        self.assertEqual(len(bounded),199)
        self.assertEqual(bounded.date.max(),pd.Timestamp('2026-11-03'))
        self.assertEqual(len(frame),200)

    def test_completed_200_rows_still_pass_length_boundary(self):
        m = collector()
        frame = pd.DataFrame(dict(date=pd.date_range(end='2026-11-04',periods=201),symbol='OLD'))
        with patch.dict(os.environ, {'GATE_BTC_DATA_CUTOFF':'2026-11-03'}):
            bounded = m.requested_cutoff_history(frame)
        self.assertEqual(len(bounded),200)

    def test_duplicate_dates_cannot_supply_200th_observation(self):
        m = collector()
        frame = pd.DataFrame(dict(date=['2026-11-02','2026-11-02'],symbol='DUP'))
        with patch.dict(os.environ, {'GATE_BTC_DATA_CUTOFF':'2026-11-03'}):
            with self.assertRaisesRegex(RuntimeError,'duplicate'):
                m.requested_cutoff_history(frame)

    def test_frozen_earlier_cutoffs_and_unscoped_replay_unchanged(self):
        m = collector()
        frame = pd.DataFrame(dict(date=['2026-11-02','2026-11-03'],symbol='X'))
        for cutoff in ('','2026-11-02'):
            with patch.dict(os.environ, {'GATE_BTC_DATA_CUTOFF':cutoff}):
                self.assertIs(m.requested_cutoff_history(frame),frame)


if __name__ == '__main__':
    unittest.main()
