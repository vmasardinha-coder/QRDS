import json
import unittest
from pathlib import Path

P = Path('tools/gate_btc_factory/GRAMMAR_007_EFFECT_CASES_AUTH_20260921.json')


def load():
    return json.loads(P.read_text(encoding='utf-8'))


class Grammar007EffectCasesAuthTests(unittest.TestCase):
    def test_frozen_before_target_read_and_safety_locks(self):
        x = load()
        self.assertEqual(x['status'], 'FROZEN_BEFORE_FIRST_TARGET_READ')
        self.assertEqual(x['target_boundary_at_freeze'], {
            'target_source_opened': False,
            'target_bytes_read': False,
            'outcomes_read': False,
            'economics_read': False,
        })
        s = x['safety']
        self.assertIs(s['RESEARCH_ONLY'], True)
        self.assertIs(s['SHADOW_ONLY'], True)
        self.assertIs(s['NOT_APPROVED'], True)
        self.assertIs(s['ENGINE_FEED'], False)
        self.assertEqual(s['ORDERS'], 0)
        self.assertEqual(s['REAL_CAPITAL'], 0)
        self.assertIs(s['NO_RETUNE'], True)
        self.assertIs(s['NO_BACKFILL'], True)
        self.assertIs(s['NO_COUNTER_RESET'], True)
        self.assertIs(s['FAIL_CLOSED'], True)

    def test_primary_is_exact_50_50_zscore_case(self):
        x = load()
        c = x['cases'][0]
        self.assertEqual(c['case_id'], 'G007_FOCUS_50_50_V1')
        self.assertEqual(c['execution_order'], 1)
        self.assertEqual(c['role'], 'PRIMARY_AUTHORIZED_CASE')
        self.assertEqual(c['weights'], {'IPCA': 0.5, 'SELIC': 0.5})
        self.assertIs(c['optimization'], False)
        self.assertIs(c['retune'], False)
        self.assertEqual(x['standardization']['method'], 'ZSCORE')
        self.assertEqual(x['standardization']['fit_partition'], 'DISCOVERY_ONLY')
        self.assertIn('reuse discovery-fitted', x['standardization']['validation_and_holdout'])

    def test_followon_component_cases_are_predeclared_and_ordered(self):
        x = load()
        ids = [c['case_id'] for c in x['cases']]
        self.assertEqual(ids, [
            'G007_FOCUS_50_50_V1',
            'G007_FOCUS_IPCA_ONLY_V1',
            'G007_FOCUS_SELIC_ONLY_V1',
        ])
        self.assertEqual(x['cases'][1]['weights'], {'IPCA': 1.0, 'SELIC': 0.0})
        self.assertEqual(x['cases'][2]['weights'], {'IPCA': 0.0, 'SELIC': 1.0})
        ec = x['execution_contract']
        self.assertIs(ec['primary_case_first'], True)
        self.assertIs(ec['followon_cases_execute_after_primary_terminal_result'], True)
        self.assertIs(ec['followon_existence_independent_of_primary_result'], True)
        self.assertIs(ec['no_cross_case_retune'], True)
        self.assertIs(ec['no_performance_based_case_creation'], True)

    def test_no_late_method_freedom_is_left_open(self):
        x = load()
        imm = set(x['immutability'])
        required = {
            'NO_RETUNE',
            'NO_BACKFILL',
            'NO_COUNTER_RESET',
            'NO_WEIGHT_OPTIMIZATION',
            'NO_COMPONENT_SELECTION_AFTER_OUTCOME',
            'NO_CASE_CREATION_AFTER_OUTCOME_FOR_THIS_BATCH',
            'NO_VALIDATION_REFIT',
            'NO_HOLDOUT_REFIT',
        }
        self.assertTrue(required <= imm)


if __name__ == '__main__':
    unittest.main()
