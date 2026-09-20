import json
import unittest
from pathlib import Path

from tools.gate_btc_factory import grammar_007_availability_authority_materializer as m

REGISTRY = Path("research/b3_h/grammar_007_availability_authority_registry.json")


class Grammar007AvailabilityAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = json.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_coverage_is_bounded_not_backfilled(self):
        self.assertEqual(self.reg["coverage"]["start"], "2024-02-05")
        self.assertEqual(self.reg["coverage"]["end"], "2026-09-20")
        self.assertEqual(self.reg["bcb_focus"]["missing_rule"], "INELIGIBLE_NO_IMPUTATION")
        self.assertTrue(self.reg["safety"]["NO_BACKFILL"])

    def test_focus_window_is_before_regular_b3_open(self):
        self.assertEqual(self.reg["bcb_focus"]["release_window_start"], "08:25")
        self.assertEqual(self.reg["bcb_focus"]["release_window_end"], "08:30")
        self.assertEqual(self.reg["b3"]["regular_cash_market_open"], "10:00")
        self.assertIn("If Monday is not a session, the week is ineligible", self.reg["bcb_focus"]["causal_eligibility_rule"])

    def test_special_sessions_and_closures_are_explicit(self):
        self.assertEqual(self.reg["b3"]["special_open"]["2024-02-14"], "13:00")
        self.assertEqual(self.reg["b3"]["special_open"]["2025-03-05"], "13:00")
        self.assertEqual(self.reg["b3"]["special_open"]["2026-02-18"], "13:00")
        for day in ("2024-12-24", "2025-03-03", "2026-09-07"):
            self.assertIn(day, self.reg["b3"]["closed_dates"])

    def test_cvm_delivery_resolver_uses_annual_history_then_monthly(self):
        urls = m.delivery_authority_urls(self.reg, ["202402", "202412", "202501", "202609"])
        historical = [x for x in urls if x["mode"] == "HISTORICAL_ANNUAL"]
        monthly = [x for x in urls if x["mode"] == "CURRENT_MONTHLY"]
        self.assertEqual(len(historical), 1)
        self.assertTrue(historical[0]["url"].endswith("/HIST/fi_entrega_documento_2024.zip"))
        self.assertEqual([x["coverage_unit"] for x in monthly], ["202501", "202609"])

    def test_target_never_gets_body_read(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        self.assertIn('target_probe = head(reg["b3"]["target_source_url"])', text)
        self.assertIn('"target_bytes_read": False', text)
        self.assertIn('"target_bytes_parsed": False', text)
        self.assertIn('"target_outcomes_read": False', text)

    def test_no_science_started(self):
        text = Path(m.__file__).read_text(encoding="utf-8")
        for literal in ('"historical_testing_started": False', '"features_materialized": False', '"candidate_ranked": False',
                        '"outcomes_read": False', '"economics_read": False', '"scientific_credit": 0'):
            self.assertIn(literal, text)


if __name__ == "__main__":
    unittest.main()
