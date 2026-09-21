import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path('tools/gate_btc_factory/grammar_007_pearson_historical_eval.py')
spec = importlib.util.spec_from_file_location('g007_eval', MODULE_PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def levels_for_targets(targets, returns):
    out = {}
    for target, ret in zip(targets, returns):
        y, mo, d = map(int, target.split('-'))
        prev = f'{y:04d}-{mo:02d}-{d-1:02d}'
        out[prev] = 100.0
        out[target] = 100.0 * (1.0 + ret)
    return out


def fixture(validation_same_sign=False, validation_zero_target_variance=False):
    discovery = ['2024-01-02', '2024-01-04', '2024-01-06', '2024-01-08']
    validation = ['2025-02-02', '2025-02-04', '2025-02-06', '2025-02-08']
    holdout = ['2026-03-02', '2026-03-04', '2026-03-06', '2026-03-08']
    rows = []
    for dates in (discovery, validation, holdout):
        for i, d in enumerate(dates, 1):
            rows.append({'target_session_date': d, m.IPCA: float(i), m.SELIC: float(i) * 2.0})
    features = {'families': {m.FAMILY: {'rows': rows}}}
    partitions = {
        'partitions_frozen': True,
        'embargo_sessions': 60,
        'partition_contract': '50_30_20_CHRONOLOGICAL',
        'candidate_partition_dates': {'discovery': discovery, 'validation': validation, 'holdout': holdout},
    }
    cases = {
        'status': 'FROZEN_BEFORE_FIRST_TARGET_READ',
        'target': 'Ibovespa simple close-to-close return for the next eligible B3 regular session after the Focus revision vector is officially observable.',
        'cases': [
            {'case_id': m.EXPECTED_CASES[0], 'execution_order': 1, 'weights': {'IPCA': .5, 'SELIC': .5}},
            {'case_id': m.EXPECTED_CASES[1], 'execution_order': 2, 'weights': {'IPCA': 1.0, 'SELIC': 0.0}},
            {'case_id': m.EXPECTED_CASES[2], 'execution_order': 3, 'weights': {'IPCA': 0.0, 'SELIC': 1.0}},
        ],
    }
    stat = {'status': 'FROZEN_BEFORE_FIRST_TARGET_READ', 'effect_statistic': {'name': 'PEARSON_PRODUCT_MOMENT_CORRELATION'}}
    route = {
        'status': 'MECHANICAL_SOURCE_ROUTE_CORRECTED_TARGET_IDENTITY_UNCHANGED',
        'provider': 'B3 S.A. - Brasil, Bolsa, Balcao',
        'scientific_changes': {
            'target_identity_changed': False, 'feature_changed': False, 'partition_changed': False,
            'pearson_changed': False, 'case_weights_changed': False, 'validation_rule_changed': False,
            'holdout_rule_changed': False,
        },
    }
    disc_rets = [.01, .02, .03, .04]
    if validation_zero_target_variance:
        val_rets = [.02, .02, .02, .02]
    else:
        val_rets = [.01, .02, .03, .04] if validation_same_sign else [.04, .03, .02, .01]
    maps = {
        2024: levels_for_targets(discovery, disc_rets),
        2025: levels_for_targets(validation, val_rets),
        2026: levels_for_targets(holdout, [.01, .02, .03, .04]),
    }
    return features, partitions, cases, stat, route, maps


class Grammar007PearsonHistoricalEvalTests(unittest.TestCase):
    def test_validation_failure_never_fetches_2026(self):
        features, partitions, cases, stat, route, maps = fixture(False)
        calls = []
        def fetch(year, _route):
            calls.append(year)
            return maps[year]
        result = m.execute(features, partitions, cases, stat, route, fetch)
        self.assertEqual(calls, [2024, 2025])
        self.assertEqual(result['status'], 'HISTORICAL_EVALUATION_COMPLETE_NO_SURVIVOR')
        self.assertFalse(result['target_source']['holdout_year_2026_ever_fetched'])
        for case in result['cases']:
            self.assertFalse(case['validation']['pass'])
            self.assertFalse(case['holdout']['started'])
            self.assertIsNone(case['holdout']['pearson_r'])
            self.assertEqual(case['terminal_status'], 'REJECTED_VALIDATION_NO_RETUNE')

    def test_validation_zero_variance_is_fail_closed_terminal_without_2026_fetch(self):
        features, partitions, cases, stat, route, maps = fixture(validation_zero_target_variance=True)
        calls = []
        def fetch(year, _route):
            calls.append(year)
            return maps[year]
        result = m.execute(features, partitions, cases, stat, route, fetch)
        self.assertEqual(calls, [2024, 2025])
        self.assertEqual(result['status'], 'HISTORICAL_EVALUATION_COMPLETE_NO_SURVIVOR')
        for case in result['cases']:
            self.assertTrue(case['validation']['started'])
            self.assertFalse(case['validation']['pass'])
            self.assertTrue(case['validation']['ineligible'])
            self.assertEqual(case['ineligibility_reason'], 'PEARSON_TARGET_ZERO_VARIANCE_FAIL_CLOSED')
            self.assertFalse(case['holdout']['started'])
            self.assertEqual(case['terminal_status'], 'REJECTED_VALIDATION_NO_RETUNE')

    def test_validation_pass_fetches_holdout_only_after_gate_for_each_case(self):
        features, partitions, cases, stat, route, maps = fixture(True)
        calls = []
        def fetch(year, _route):
            calls.append(year)
            return maps[year]
        result = m.execute(features, partitions, cases, stat, route, fetch)
        self.assertEqual(calls[:2], [2024, 2025])
        self.assertEqual(calls[2:], [2026, 2026, 2026])
        self.assertTrue(result['target_source']['holdout_year_2026_ever_fetched'])
        for case in result['cases']:
            self.assertTrue(case['validation']['pass'])
            self.assertTrue(case['holdout']['started'])
            self.assertTrue(case['holdout']['pass'])
            self.assertTrue(case['terminal_status'].startswith('SURVIVOR_'))

    def test_ptbr_index_parser(self):
        self.assertEqual(m.parse_ptbr_number('131.147,29'), 131147.29)
        self.assertIsNone(m.parse_ptbr_number(None))

    def test_pearson(self):
        self.assertAlmostEqual(m.sample_pearson([1,2,3,4], [2,4,6,8]), 1.0)
        self.assertAlmostEqual(m.sample_pearson([1,2,3,4], [8,6,4,2]), -1.0)
        with self.assertRaises(m.ScientificIneligible):
            m.sample_pearson([1,2,3,4], [2,2,2,2])


if __name__ == '__main__':
    unittest.main()
