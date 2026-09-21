import unittest
from pathlib import Path

from tools.gate_btc_factory import grammar_007_causal_feature_materializer as m


class Grammar007CausalFeatureMaterializerTests(unittest.TestCase):
    def test_safety_locks(self):
        self.assertTrue(m.SAFETY["RESEARCH_ONLY"])
        self.assertTrue(m.SAFETY["SHADOW_ONLY"])
        self.assertTrue(m.SAFETY["NOT_APPROVED"])
        self.assertFalse(m.SAFETY["ENGINE_FEED"])
        self.assertEqual(m.SAFETY["ORDERS"], 0)
        self.assertEqual(m.SAFETY["REAL_CAPITAL"], 0)
        self.assertTrue(m.SAFETY["NO_BACKFILL"])
        self.assertTrue(m.SAFETY["NO_RETUNE"])
        self.assertTrue(m.SAFETY["FAIL_CLOSED"])

    def test_no_target_source_is_defined_or_opened(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        self.assertNotIn("COTAHIST_", text)
        self.assertIn('"target_source_opened": False', text)
        self.assertIn('"target_bytes_read": False', text)
        self.assertIn('"outcomes_read": False', text)
        self.assertIn('"economics_read": False', text)

    def test_candidate_universe_is_not_yet_frozen_by_materializer(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn('"candidate_universe_frozen": False', text)
        self.assertIn('"validation_started": False', text)
        self.assertIn('"historical_testing_started": False', text)
        self.assertIn('"candidate_ranked": False', text)
        self.assertIn('"next_gate": "FREEZE_CANDIDATE_UNIVERSE_BEFORE_TARGET_READ"', text)

    def test_frozen_feature_names_are_exact(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn("IPCA_CURRENT_YEAR_MEDIAN_REVISION", text)
        self.assertIn("SELIC_CURRENT_YEAR_END_MEDIAN_REVISION", text)
        self.assertIn("EQUITY_FUND_AGG_NET_FLOW_OVER_PRIOR_AGG_NAV", text)
        self.assertIn("XAGRAMMAR_728DC88D691B", text)
        self.assertIn("XAGRAMMAR_62943307741A", text)

    def test_cvm_transition_is_fail_closed(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn("2024-09-30", text)
        self.assertIn("HISTORICAL_CLASS_VERSIONING_NOT_YET_PROVEN_FOR_REGISTRO_CLASSE", text)
        self.assertIn("post_rcvm175_dates_ineligible", text)

    def test_focus_ambiguity_is_ineligible_not_selected(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn("AMBIGUOUS_BASECALCULO_MEDIANA", text)
        self.assertIn("len(values) != 1", text)

    def test_materializer_network_boundary_remains_source_only(self):
        # Mechanical rerun anchor: keeps CI retrigger explicit without changing science.
        self.assertTrue(m.BCB_BASE.startswith("https://olinda.bcb.gov.br/"))
        self.assertTrue(m.CVM_INF.startswith("https://dados.cvm.gov.br/"))


if __name__ == "__main__":
    unittest.main()
