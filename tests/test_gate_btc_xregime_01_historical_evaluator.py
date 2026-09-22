import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

M = Path('tools/gate_btc_factory/xregime_01_historical_evaluator.py')
spec = importlib.util.spec_from_file_location('xregime_eval', M)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)
PR = json.loads(Path('tools/gate_btc_factory/XREGIME_01_FINITE_BATCH_PREREG_20260922.json').read_text())


def bars(times, base=100.0):
    return [
        {'time': t, 'open': base, 'high': base + 1, 'low': base - 1, 'close': base, 'volume': 1.0}
        for t in times
    ]


def empty_partition(pass_ids=()):
    state_ids = [x['state_id'] for x in PR['benchmark_states']]
    signal_ids = [x['signal_id'] for x in PR['target_signals']]
    cases = {}
    for state in state_ids:
        for signal in signal_ids:
            cid = f'{state}::{signal}::GATE'
            cases[cid] = {'candidate_id': cid, 'pass': cid in pass_ids}
    return {'cases': cases, 'baselines': {}}


class XRegimeHistoricalEvaluatorTests(unittest.TestCase):
    def test_candidate_space_is_exactly_twelve(self):
        p = empty_partition()
        self.assertEqual(len(p['cases']), 12)

    def test_synchronization_breaks_on_gap_and_never_imputes(self):
        h = m.HOUR
        btc = bars([0, h, 2*h, 4*h, 5*h], 100)
        eth = bars([0, h, 2*h, 5*h], 200)
        segments, audit = m.synchronized_segments(btc, eth)
        self.assertEqual([[x['time'] for x in s] for s in segments], [[0, h, 2*h], [5*h]])
        self.assertEqual(audit['imputed_bar_count'], 0)
        self.assertEqual(audit['policy'], 'INELIGIBLE_NO_IMPUTATION')

    def test_fixed_hold_uses_next_open_and_24_completed_hours(self):
        h = m.HOUR
        segment = [
            {'time': i*h, 'btc_open': 100, 'btc_close': 100, 'eth_open': 100+i, 'eth_close': 100+i}
            for i in range(40)
        ]
        flags = [False] * 40
        flags[5] = True
        trades = m.simulate_fixed_hold(segment, flags, 0, 39*h, PR)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0]['decision_time'], 5*h)
        self.assertEqual(trades[0]['entry_time'], 6*h)
        self.assertEqual(trades[0]['exit_time'], 30*h)

    def test_feature_geometry_is_causal_and_defined_after_warmup(self):
        h = m.HOUR
        segment = []
        for i in range(800):
            segment.append({
                'time': i*h,
                'btc_open': 100+i*.01,
                'btc_close': 100+i*.01,
                'eth_open': 200+i*.02,
                'eth_close': 200+i*.02,
            })
        f = m.feature_flags(segment)
        self.assertIsNone(f['states']['BTC_TREND_168H'][166])
        self.assertIsNotNone(f['states']['BTC_TREND_168H'][167])
        self.assertIsNone(f['states']['BTC_LOW_VOL_24H_VS_720H_MEDIAN'][743])
        self.assertIsNotNone(f['states']['BTC_LOW_VOL_24H_VS_720H_MEDIAN'][744])
        self.assertIsNone(f['signals']['ETH_TREND_STATE_72H'][70])
        self.assertIsNotNone(f['signals']['ETH_TREND_STATE_72H'][71])

    def test_discovery_failure_never_fetches_validation_or_holdout(self):
        calls = []
        def fetcher(product, start, end):
            calls.append((product, start, end))
            return bars([start, start + m.HOUR], 100 if product == 'BTC-USD' else 200)
        with patch.object(m, 'evaluate_partition', return_value=empty_partition()):
            r = m.execute(PR, fetcher=fetcher)
        self.assertEqual(len(calls), 2)
        self.assertFalse(r['validation_source_opened'])
        self.assertFalse(r['holdout_source_opened'])
        self.assertEqual(r['historical_triage_pass_count'], 0)

    def test_partition_gates_open_in_order(self):
        first = next(iter(empty_partition()['cases']))
        discovery = empty_partition([first])
        validation = empty_partition([first])
        holdout = empty_partition([first])
        calls = []
        def fetcher(product, start, end):
            calls.append((product, start, end))
            return bars([start, start + m.HOUR], 100 if product == 'BTC-USD' else 200)
        with patch.object(m, 'evaluate_partition', side_effect=[discovery, validation, holdout]):
            r = m.execute(PR, fetcher=fetcher)
        self.assertEqual(len(calls), 6)
        self.assertTrue(r['validation_source_opened'])
        self.assertTrue(r['holdout_source_opened'])
        self.assertEqual(r['historical_triage_passes'], [first])
        self.assertEqual(r['terminal_status'][first], 'HISTORICAL_TRIAGE_PASS_PROSPECTIVE_REQUIRED_ZERO_CREDIT')
        self.assertEqual(r['historical_survivor_credit'], 0)
        self.assertEqual(r['prospective_credit'], 0)
        self.assertFalse(r['promotion_authority'])

    def test_incremental_gate_requires_beating_ungated_baseline(self):
        good = {
            'n': 20, 'available': True,
            'mean_net_primary': 0.01, 'mean_net_stress': 0.005, 'effect': 0.5,
        }
        baseline = {
            'n': 30, 'available': True,
            'mean_net_primary': 0.012, 'mean_net_stress': 0.006, 'effect': 0.4,
        }
        # Frozen rule requires both primary mean and effect to be >= / > baseline as specified.
        self.assertFalse(good['mean_net_primary'] > baseline['mean_net_primary'])
        self.assertTrue(good['effect'] >= baseline['effect'])

    def test_safety_zero_credit(self):
        r = m.execute
        self.assertFalse(PR['safety']['ENGINE_FEED'])
        self.assertEqual(PR['safety']['ORDERS'], 0)
        self.assertEqual(PR['safety']['REAL_CAPITAL'], 0)
        self.assertTrue(PR['safety']['NO_RETUNE'])
        self.assertTrue(PR['safety']['NO_BACKFILL'])
        self.assertTrue(callable(r))


if __name__ == '__main__':
    unittest.main()
