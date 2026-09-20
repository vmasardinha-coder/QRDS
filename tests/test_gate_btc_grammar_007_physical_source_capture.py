import unittest
from pathlib import Path

from tools.gate_btc_factory import grammar_007_physical_source_capture as p


class Grammar007PhysicalSourceCaptureTests(unittest.TestCase):
    """Outcome-blind source reachability/provenance boundary only."""

    def test_source_contract_is_exact_and_official_only(self):
        self.assertTrue(p.BCB_ANNUAL.startswith("https://olinda.bcb.gov.br/"))
        self.assertTrue(p.CVM_INF_SAMPLE.startswith("https://dados.cvm.gov.br/"))
        self.assertTrue(p.CVM_DELIVERY_SAMPLE.startswith("https://dados.cvm.gov.br/"))
        self.assertTrue(p.CVM_CLASS_REGISTRY.startswith("https://dados.cvm.gov.br/"))
        self.assertTrue(all(url.startswith("https://bvmf.bmfbovespa.com.br/") for url in p.B3_COTAHIST_CANDIDATES))

    def test_b3_target_is_never_parsed_in_capture_stage(self):
        text = Path(p.__file__).read_text(encoding="utf-8")
        self.assertIn('"target_bytes_parsed":False', text)
        self.assertIn('"target_outcomes_read":False', text)
        self.assertIn('"outcomes_read":False', text)
        self.assertIn('"economics_read":False', text)
        self.assertIn('"features_materialized":False', text)
        self.assertIn('"candidate_ranked":False', text)

    def test_pit_is_fail_closed_until_semantics_are_materialized(self):
        text = Path(p.__file__).read_text(encoding="utf-8")
        self.assertIn('"exact_historical_intraday_publication_timestamp_proven":False', text)
        self.assertIn('"availability_mapping_requires_delivery_join":True', text)
        self.assertGreaterEqual(text.count('"pit_admission_pass":False'), 3)

    def test_scientific_credit_stays_zero(self):
        self.assertTrue(p.SAFETY["RESEARCH_ONLY"])
        self.assertTrue(p.SAFETY["SHADOW_ONLY"])
        self.assertTrue(p.SAFETY["NOT_APPROVED"])
        self.assertFalse(p.SAFETY["ENGINE_FEED"])
        self.assertEqual(p.SAFETY["ORDERS"], 0)
        self.assertEqual(p.SAFETY["REAL_CAPITAL"], 0)
        self.assertTrue(p.SAFETY["NO_BACKFILL"])
        self.assertTrue(p.SAFETY["NO_RETUNE"])
        self.assertTrue(p.SAFETY["FAIL_CLOSED"])

    def test_feature_source_fields_match_frozen_materializer_contract(self):
        text = Path(p.__file__).read_text(encoding="utf-8")
        for field in ("DT_COMPTC", "CAPTC_DIA", "RESG_DIA", "VL_PATRIM_LIQ"):
            self.assertIn(field, text)
        for field in ("Indicador", "Data", "DataReferencia", "Mediana", "baseCalculo"):
            self.assertIn(field, text)


if __name__ == "__main__":
    unittest.main()
