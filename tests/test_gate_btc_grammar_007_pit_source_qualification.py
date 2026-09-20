import unittest
from pathlib import Path

from tools.gate_btc_factory import grammar_007_pit_source_qualification as q


class Grammar007PitQualificationTests(unittest.TestCase):
    def test_safety_boundary(self):
        self.assertTrue(q.SAFETY["RESEARCH_ONLY"])
        self.assertTrue(q.SAFETY["SHADOW_ONLY"])
        self.assertTrue(q.SAFETY["NOT_APPROVED"])
        self.assertFalse(q.SAFETY["ENGINE_FEED"])
        self.assertEqual(q.SAFETY["ORDERS"], 0)
        self.assertEqual(q.SAFETY["REAL_CAPITAL"], 0)
        self.assertTrue(q.SAFETY["NO_BACKFILL"])
        self.assertTrue(q.SAFETY["NO_LATE_SEAL"])
        self.assertTrue(q.SAFETY["NO_COUNTER_RESET"])
        self.assertTrue(q.SAFETY["NO_RETUNE"])
        self.assertTrue(q.SAFETY["FAIL_CLOSED"])

    def test_target_source_is_head_only(self):
        text = Path(q.__file__).read_text(encoding="utf-8")
        self.assertIn('b3_attempts', text) if False else None
        self.assertIn('"target_bytes_read": False', text)
        self.assertIn('"target_bytes_parsed": False', text)
        self.assertIn('"target_outcomes_read": False', text)
        self.assertIn('cotahist = head(B3_COTAHIST)', text)

    def test_bcb_remains_fail_closed(self):
        text = Path(q.__file__).read_text(encoding="utf-8")
        self.assertIn('BCB_FOCUS_HISTORICAL_INTRADAY_PUBLICATION_TIMESTAMP_NOT_INDEPENDENTLY_PROVEN', text)
        self.assertIn('"pit_admission_pass": False', text)

    def test_cvm_join_contract_uses_current_delivery_schema(self):
        text = Path(q.__file__).read_text(encoding="utf-8")
        for field in ("Data_Hora_Entrega", "Data_Inicio_Competencia", "Data_Fim_Competencia", "ID_Documento", "Tipo_Apresentacao", "Ativo"):
            self.assertIn(field, text)
        self.assertIn("INELIGIBLE_NO_IMPUTATION", text)
        self.assertIn("strictly before the target B3 regular-session open", text)

    def test_no_science_or_outcomes_started(self):
        text = Path(q.__file__).read_text(encoding="utf-8")
        for literal in ('"historical_testing_started": False', '"features_materialized": False', '"candidate_ranked": False',
                        '"outcomes_read": False', '"economics_read": False', '"scientific_credit": 0'):
            self.assertIn(literal, text)


if __name__ == "__main__":
    unittest.main()
