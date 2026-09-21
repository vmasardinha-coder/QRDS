import json
import unittest
from pathlib import Path

P = Path('tools/gate_btc_factory/GRAMMAR_007_EFFECT_STAT_AUTH_20260921.json')


def load():
    return json.loads(P.read_text(encoding='utf-8'))


class Grammar007EffectStatAuthTests(unittest.TestCase):
    def test_frozen_before_target_read(self):
        x = load()
        self.assertEqual(x['status'], 'FROZEN_BEFORE_FIRST_TARGET_READ')
        self.assertEqual(x['authorization'], 'USER_AUTHORIZED_PEARSON_2026-09-21')
        self.assertEqual(x['target_boundary_at_freeze'], {
            'target_source_opened': False,
            'target_bytes_read': False,
            'outcomes_read': False,
            'economics_read': False,
        })

    def test_exact_statistic_and_cases(self):
        x = load()
        e = x['effect_statistic']
        self.assertEqual(e['name'], 'PEARSON_PRODUCT_MOMENT_CORRELATION')
        self.assertEqual(e['standardized_effect'], 'Pearson r itself; dimensionless in [-1,1]')
        self.assertIs(e['alternate_estimators'], False)
        self.assertIs(e['post_outcome_metric_selection'], False)
        self.assertEqual(x['execution_order'], [
            'G007_FOCUS_50_50_V1',
            'G007_FOCUS_IPCA_ONLY_V1',
            'G007_FOCUS_SELIC_ONLY_V1',
        ])

    def test_target_and_partition_are_already_frozen_contracts(self):
        x = load()
        self.assertEqual(
            x['target'],
            'Ibovespa simple close-to-close return for the next eligible B3 regular session after the Focus revision vector is officially observable.'
        )
        p = x['partition_contract']
        self.assertEqual(p['rule'], '50_30_20_CHRONOLOGICAL')
        self.assertEqual(p['embargo_sessions'], 60)
        self.assertIs(p['reuse_exact_same_sealed_partitions_for_all_cases'], True)

    def test_validation_and_holdout_rule(self):
        x = load()['discovery_validation_holdout_contract']
        self.assertIn('abs(r_validation) >= 0.50 * abs(r_discovery)', x['validation_pass'])
        self.assertEqual(x['validation_failure'], 'REJECT_NO_RETUNE')
        self.assertEqual(x['holdout_read_gate'], 'holdout is unread unless validation passes')
        self.assertIn('abs(r_holdout) >= 0.50 * abs(r_discovery)', x['holdout_pass'])
        self.assertEqual(x['holdout_failure'], 'REJECT_NO_RETUNE')

    def test_safety_locks(self):
        s = load()['safety']
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
        self.assertIs(s['H1_H31_UNTOUCHED'], True)


if __name__ == '__main__':
    unittest.main()
