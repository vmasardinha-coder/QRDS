from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "tools/gate_btc_2_master_plan_16_systems.md"

EXPECTED = {
    1: "Collection Health / Gates",
    2: "Anti-look-ahead / recursivity",
    3: "ml4t / PurgedCV",
    4: "VectorBT",
    5: "Jesse",
    6: "PyBroker",
    7: "Freqtrade",
    8: "Cryptofeed",
    9: "hftbacktest",
    10: "NautilusTrader",
    11: "LOB",
    12: "ml4t / independent backtest",
    13: "Qlib",
    14: "Barter-rs",
    15: "LEAN / B3",
    16: "RL / LLM Agents / public strategies",
}


class GateBtc2MasterPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAN.read_text(encoding="utf-8")

    def test_exact_16_system_numbering_and_names(self):
        rows = {}
        for line in self.text.splitlines():
            match = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", line)
            if match:
                rows[int(match.group(1))] = match.group(2).strip()
        self.assertEqual(rows, EXPECTED)

    def test_factory_is_cross_cutting_not_phase_17(self):
        self.assertIn("not a phase 17", self.text)
        self.assertIn("Strategy Factory — discovery owner", self.text)
        self.assertIn("Evidence Factory — evidence adjudication owner", self.text)
        self.assertIn("Collector Supervisor — shared operational owner", self.text)
        self.assertNotRegex(self.text, r"\|\s*17\s*\|")

    def test_resume_order_and_deferred_frontier_are_frozen(self):
        self.assertIn("8 Cryptofeed/data path → 9 hftbacktest/Stage 9 → 10 Nautilus/event parity → 11 LOB → 12 independent replication → 13 Qlib/ML → 14 Barter-rs", self.text)
        self.assertIn("System 15 / LEAN-B3 + Strategy Factory continues in parallel", self.text)
        self.assertIn("System 16 remains deliberately deferred", self.text)

    def test_stage9_implementation_is_not_evidence(self):
        self.assertIn("Stage 9 implementation/builder/workflow existence is not prospective evidence", self.text)
        self.assertIn("Only authorized forward-only observations can earn prospective credit", self.text)
        self.assertIn("If evidence is valid but insufficient, remain `COLLECT_MORE`", self.text)

    def test_permanent_zero_capital_boundary(self):
        for required in (
            "`RESEARCH_ONLY=true`",
            "`SHADOW_ONLY=true`",
            "`NOT_APPROVED=true`",
            "`ENGINE_FEED=false`",
            "`ORDERS=0`",
            "`REAL_CAPITAL_BRL=0`",
        ):
            self.assertIn(required, self.text)
        self.assertIn("no automatic promotion to real capital", self.text)

    def test_qos_refutation_does_not_invalidate_infrastructure(self):
        self.assertIn("Selector Alpha/QOS incremental-alpha hypothesis is closed/refuted", self.text)
        self.assertIn("it does not invalidate Gate BTC 2.0 infrastructure", self.text)


if __name__ == "__main__":
    unittest.main()
