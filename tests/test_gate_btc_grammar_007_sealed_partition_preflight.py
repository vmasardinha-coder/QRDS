import unittest
from pathlib import Path

from tools.gate_btc_factory import grammar_007_sealed_partition_preflight as p


class Grammar007SealedPartitionPreflightTests(unittest.TestCase):
    def test_exact_005_split_geometry_with_60_session_embargo(self):
        ds=[f"S{i:03d}" for i in range(656)]
        x=p.split_sessions(ds)
        self.assertEqual(len(x['discovery']),268)
        self.assertEqual(len(x['validation']),76)
        self.assertEqual(len(x['holdout']),72)
        self.assertEqual(x['discovery'][-1],'S267')
        self.assertEqual(x['validation'][0],'S388')
        self.assertEqual(x['validation'][-1],'S463')
        self.assertEqual(x['holdout'][0],'S584')

    def test_vector_effect_is_explicitly_blocked_before_target(self):
        self.assertEqual(p.EMBARGO,60)
        self.assertEqual(p.VECTOR_EFFECT_BLOCKER,'FOCUS_TWO_COMPONENT_VECTOR_STANDARDIZED_EFFECT_SCALARIZATION_NOT_PREREGISTERED')
        text=Path(p.__file__).read_text(encoding='utf-8')
        self.assertIn('"target_source_opened": False',text)
        self.assertIn('"target_bytes_read": False',text)
        self.assertIn('"outcomes_read": False',text)
        self.assertIn('"economics_read": False',text)
        self.assertIn('"partitions_frozen": True',text)
        self.assertIn('fit_regression_or_projection_using_target',text)
        self.assertIn('choose_norm_or_sign_rule_after_target_read',text)

    def test_no_target_source_identifier_is_present(self):
        text=Path(p.__file__).read_text(encoding='utf-8')
        self.assertNotIn('COTAHIST_',text)
        self.assertNotIn('Ibovespa close',text)

    def test_safety_locks(self):
        self.assertTrue(p.SAFETY['RESEARCH_ONLY'])
        self.assertTrue(p.SAFETY['SHADOW_ONLY'])
        self.assertTrue(p.SAFETY['NOT_APPROVED'])
        self.assertFalse(p.SAFETY['ENGINE_FEED'])
        self.assertEqual(p.SAFETY['ORDERS'],0)
        self.assertEqual(p.SAFETY['REAL_CAPITAL'],0)
        self.assertTrue(p.SAFETY['NO_BACKFILL'])
        self.assertTrue(p.SAFETY['NO_RETUNE'])
        self.assertTrue(p.SAFETY['FAIL_CLOSED'])


if __name__=='__main__':
    unittest.main()
