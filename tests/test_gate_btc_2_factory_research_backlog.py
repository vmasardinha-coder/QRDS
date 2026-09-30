import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gate_btc_2_factory_research_backlog import build


class T(unittest.TestCase):
    def test_registry_families_are_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            docs = root / "crypto_decision_lab/docs"
            docs.mkdir(parents=True)
            (docs / "GATE_BTC_2_HYPOTHESIS_REGISTRY.md").write_text(
                "# Gate BTC 2.0 — Hypothesis Registry\nRegistered: 2026-08-25\n\n"
                "| Family | Status | Data-readiness | Engine weight | Prospective eligibility |\n"
                "|---|---|---|---:|---|\n"
                "| H-LIQ | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |\n"
                "| H-BEH | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |\n"
                "| H-LIQxBEH | REGISTERED_FOR_RESEARCH | DEPENDS_ON_H-LIQ/H-BEH | 0 | NOT_ELIGIBLE |\n"
                "| H-RWA | REGISTERED_STRUCTURAL_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |\n\n"
                "| unrelated | must | never | become | family |\n", encoding="utf-8")
            (docs / "GATE_BTC_2_HYPOTHESIS_AI_CREDIT.md").write_text(
                "# Gate BTC 2.0 — H-AI-CREDIT-LIQ\nStatus: REGISTERED_FOR_RESEARCH\n"
                "Prospective eligibility: NOT_ELIGIBLE\nEngine weight: 0\nRegistered: 2026-09-24\n", encoding="utf-8")
            x = build(root)
            self.assertEqual(x["summary"]["registered_hypothesis_documents"], 2)
            self.assertEqual(x["summary"]["registered_family_count"], 5)
            self.assertEqual(x["summary"]["not_eligible_count"], 5)
            self.assertEqual({r["family_id"] for r in x["families"]}, {"H-LIQ", "H-BEH", "H-LIQxBEH", "H-RWA", "H-AI-CREDIT-LIQ"})
            self.assertTrue(all(r["engine_weight"] == "0" for r in x["families"]))
            self.assertFalse(x["authority"]["source_admission_authority"])
            self.assertEqual(x["authority"]["scientific_credit"], 0)


if __name__ == "__main__":
    unittest.main()
