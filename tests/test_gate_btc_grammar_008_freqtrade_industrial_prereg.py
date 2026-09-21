import json
import unittest
from pathlib import Path

P=Path('tools/gate_btc_factory/GRAMMAR_008_FREQTRADE_INDUSTRIAL_PREREG_20260921.json')

class Grammar008PreregTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(P.read_text())
    def test_frozen_before_outcomes(self):
        x=self.x
        self.assertEqual(x['status'],'FROZEN_BEFORE_SOURCE_OUTCOME_READ')
        self.assertEqual(x['target_boundary_at_freeze'],{'grammar_008_market_data_fetched':False,'outcomes_read':False,'economics_read':False})
        self.assertTrue(x['safety']['RESEARCH_ONLY']);self.assertTrue(x['safety']['SHADOW_ONLY'])
        self.assertFalse(x['safety']['ENGINE_FEED']);self.assertEqual(x['safety']['ORDERS'],0);self.assertEqual(x['safety']['REAL_CAPITAL'],0)
    def test_candidate_count_is_finite_and_exact(self):
        x=self.x
        variants=sum(len(f['variants']) for f in x['families'])
        self.assertEqual(variants,12)
        self.assertEqual(len(x['market_data']['products']),2)
        self.assertEqual(x['candidate_count'],24)
        ids=[(f['family_id'],v['variant_id'],a) for f in x['families'] for v in f['variants'] for a in x['market_data']['products']]
        self.assertEqual(len(ids),len(set(ids)))
    def test_partition_and_holdout_blindness(self):
        x=self.x
        self.assertEqual(x['partitions']['boundary_embargo_hours'],168)
        self.assertTrue(x['partitions']['validation_unread_until_discovery_gate'])
        self.assertTrue(x['partitions']['holdout_unread_until_validation_gate'])
        self.assertTrue(x['decision_rule']['no_retune_after_any_partition'])
    def test_costs_are_fixed_before_outcome(self):
        c=self.x['costs']
        self.assertEqual(c['primary_bps_per_side'],20)
        self.assertEqual(c['stress_bps_per_side'],40)
        self.assertTrue(c['no_cost_optimization'])
    def test_intake_seeds_are_alpha_only(self):
        self.assertEqual(self.x['included_seed_ids'],['FT-HYP-002','FT-HYP-003','FT-HYP-004'])
        self.assertIn('EXECUTION_OVERLAY_ONLY',self.x['excluded_seed']['FT-HYP-001'])

if __name__=='__main__': unittest.main()
