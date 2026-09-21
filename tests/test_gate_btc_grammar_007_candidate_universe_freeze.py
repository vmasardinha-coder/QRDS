import unittest
from pathlib import Path

from tools.gate_btc_factory import grammar_007_candidate_universe_freeze as f


class Grammar007CandidateUniverseFreezeTests(unittest.TestCase):
    def test_exact_surviving_candidate_identity(self):
        self.assertEqual(f.FOCUS_FAMILY, "XAGRAMMAR_728DC88D691B")
        self.assertEqual(f.FOCUS_COMPONENTS, [
            "IPCA_CURRENT_YEAR_MEDIAN_REVISION",
            "SELIC_CURRENT_YEAR_END_MEDIAN_REVISION",
        ])

    def test_source_blocked_family_is_not_candidate(self):
        self.assertEqual(f.CVM_FAMILY, "XAGRAMMAR_62943307741A")
        text = Path(f.__file__).read_text(encoding="utf-8")
        self.assertIn("SOURCE_INELIGIBILITY_ONLY_NOT_PERFORMANCE", text)

    def test_no_target_read_before_freeze(self):
        text = Path(f.__file__).read_text(encoding="utf-8")
        for literal in (
            '"candidate_universe_frozen": True',
            '"target_source_opened": False',
            '"target_bytes_read": False',
            '"outcomes_read": False',
            '"economics_read": False',
            '"validation_started": False',
            '"historical_testing_started": False',
            '"candidate_ranked": False',
        ):
            self.assertIn(literal, text)

    def test_no_new_search_degrees_of_freedom(self):
        text = Path(f.__file__).read_text(encoding="utf-8")
        self.assertIn('"feature_transform": "NONE"', text)
        self.assertIn('"threshold": None', text)
        self.assertIn('"lookback_grid": None', text)
        self.assertIn('"window_grid": None', text)
        self.assertIn('"target_grid": None', text)
        self.assertIn('"performance_based_source_selection": False', text)

    def test_partition_and_embargo_are_inherited(self):
        text = Path(f.__file__).read_text(encoding="utf-8")
        self.assertIn('"50_30_20_CHRONOLOGICAL"', text)
        self.assertIn('== 60', text)

    def test_safety_locks(self):
        self.assertTrue(f.SAFETY["RESEARCH_ONLY"])
        self.assertTrue(f.SAFETY["SHADOW_ONLY"])
        self.assertTrue(f.SAFETY["NOT_APPROVED"])
        self.assertFalse(f.SAFETY["ENGINE_FEED"])
        self.assertEqual(f.SAFETY["ORDERS"], 0)
        self.assertEqual(f.SAFETY["REAL_CAPITAL"], 0)
        self.assertTrue(f.SAFETY["NO_BACKFILL"])
        self.assertTrue(f.SAFETY["NO_RETUNE"])
        self.assertTrue(f.SAFETY["FAIL_CLOSED"])


if __name__ == "__main__":
    unittest.main()
