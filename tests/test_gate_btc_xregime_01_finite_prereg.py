import json
import unittest
from pathlib import Path

P = Path('tools/gate_btc_factory/XREGIME_01_FINITE_BATCH_PREREG_20260922.json')


class XRegime01FinitePreregTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = json.loads(P.read_text(encoding='utf-8'))

    def test_frozen_before_outcomes(self):
        x = self.x
        self.assertEqual(x['status'], 'FROZEN_BEFORE_BATCH_OUTCOME_READ')
        self.assertFalse(x['scientific_boundary']['batch_outcomes_read_before_freeze'])
        self.assertFalse(x['scientific_boundary']['external_performance_imported'])
        self.assertFalse(x['scientific_boundary']['external_winner_parameters_imported'])
        self.assertTrue(x['scientific_boundary']['prospective_confirmation_required_for_any_promotion'])
        self.assertTrue(x['scientific_boundary']['no_grid_extension_after_outcome'])

    def test_finite_batch(self):
        x = self.x
        self.assertEqual(x['family_id'], 'H-XREGIME-01')
        self.assertEqual(len(x['benchmark_states']), 4)
        self.assertEqual(len(x['target_signals']), 3)
        self.assertEqual(x['interaction']['form'], 'GATE')
        self.assertEqual(x['candidate_construction']['candidate_count'], 12)
        self.assertEqual(
            x['candidate_construction']['candidate_count'],
            len(x['benchmark_states']) * len(x['target_signals'])
        )

    def test_asset_choice_does_not_use_external_replication_outcomes(self):
        x = self.x
        self.assertEqual(x['market_data']['products'], ['BTC-USD', 'ETH-USD'])
        self.assertFalse(x['asset_selection_rationale']['external_replication_list_used_for_target_selection'])

    def test_blind_partition_order(self):
        p = self.x['partitions']
        self.assertEqual(p['boundary_embargo_hours'], 168)
        self.assertTrue(p['validation_unread_until_discovery_gate'])
        self.assertTrue(p['holdout_unread_until_validation_gate'])

    def test_incremental_gate_and_costs_frozen(self):
        x = self.x
        self.assertTrue(x['metrics']['incremental_vs_ungated_baseline_required'])
        self.assertEqual(x['costs']['primary_bps_per_side'], 20)
        self.assertEqual(x['costs']['stress_bps_per_side'], 40)
        self.assertTrue(x['costs']['no_cost_optimization'])
        self.assertEqual(x['interaction']['holding_period_hours'], 24)
        self.assertFalse(x['interaction']['same_bar_execution'])

    def test_historical_cannot_promote(self):
        d = self.x['decision_rule']
        self.assertEqual(d['historical_survivor_credit'], 0)
        self.assertEqual(d['prospective_credit'], 0)
        self.assertFalse(d['promotion_authority'])
        self.assertTrue(d['no_retune_after_any_partition'])

    def test_safety(self):
        s = self.x['safety']
        self.assertTrue(s['RESEARCH_ONLY'])
        self.assertTrue(s['SHADOW_ONLY'])
        self.assertFalse(s['ENGINE_FEED'])
        self.assertEqual(s['ORDERS'], 0)
        self.assertEqual(s['REAL_CAPITAL'], 0)
        self.assertTrue(s['NO_RETUNE'])
        self.assertTrue(s['NO_BACKFILL'])
        self.assertTrue(s['FAIL_CLOSED'])


if __name__ == '__main__':
    unittest.main()
