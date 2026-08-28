from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

BASE_SPEC = importlib.util.spec_from_file_location("gate_btc_2_evidence_factory", TOOLS / "gate_btc_2_evidence_factory.py")
assert BASE_SPEC and BASE_SPEC.loader
EF = importlib.util.module_from_spec(BASE_SPEC)
sys.modules["gate_btc_2_evidence_factory"] = EF
BASE_SPEC.loader.exec_module(EF)

LEDGER_SPEC = importlib.util.spec_from_file_location("gate_btc_2_evidence_transition_ledger", TOOLS / "gate_btc_2_evidence_transition_ledger.py")
assert LEDGER_SPEC and LEDGER_SPEC.loader
LEDGER = importlib.util.module_from_spec(LEDGER_SPEC)
LEDGER_SPEC.loader.exec_module(LEDGER)


def h(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


class EvidenceTransitionLedgerTests(unittest.TestCase):
    def test_append_and_verify_hash_linked_chain(self):
        candidate = h("candidate")
        first = EF.transition(candidate, "RESEARCH_CANDIDATE", "FROZEN_HYPOTHESIS", "freeze")
        second = EF.transition(candidate, "FROZEN_HYPOTHESIS", "PIT_REQUIRED", "pit", first["transition_sha256"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            s1 = LEDGER.append_transition_record(path, first)
            self.assertEqual(s1["records"], 1)
            s2 = LEDGER.append_transition_record(path, second)
            self.assertEqual(s2["records"], 2)
            self.assertEqual(s2["head_state"], "PIT_REQUIRED")
            reread = LEDGER.read_transition_ledger(path)
            self.assertEqual(reread, [first, second])
            self.assertEqual(len(LEDGER.file_sha256(path)), 64)

    def test_refuses_transition_fork(self):
        candidate = h("candidate")
        first = EF.transition(candidate, "RESEARCH_CANDIDATE", "FROZEN_HYPOTHESIS", "freeze")
        wrong = EF.transition(candidate, "FROZEN_HYPOTHESIS", "PIT_REQUIRED", "pit", h("wrong-prior"))
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            LEDGER.append_transition_record(path, first)
            with self.assertRaises(RuntimeError):
                LEDGER.append_transition_record(path, wrong)

    def test_detects_historical_mutation(self):
        candidate = h("candidate")
        first = EF.transition(candidate, "RESEARCH_CANDIDATE", "FROZEN_HYPOTHESIS", "freeze")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            LEDGER.append_transition_record(path, first)
            row = json.loads(path.read_text())
            row["reason"] = "mutated after append"
            path.write_text(json.dumps(row) + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                LEDGER.read_transition_ledger(path)

    def test_detects_removed_middle_record(self):
        candidate = h("candidate")
        first = EF.transition(candidate, "RESEARCH_CANDIDATE", "FROZEN_HYPOTHESIS", "freeze")
        second = EF.transition(candidate, "FROZEN_HYPOTHESIS", "PIT_REQUIRED", "pit", first["transition_sha256"])
        third = EF.transition(candidate, "PIT_REQUIRED", "PIT_PASS", "pit pass", second["transition_sha256"])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "ledger.jsonl"
            for row in (first, second, third):
                LEDGER.append_transition_record(path, row)
            path.write_text("\n".join(json.dumps(x) for x in (first, third)) + "\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                LEDGER.read_transition_ledger(path)

    def test_zero_capital_boundary_is_inherited(self):
        self.assertTrue(LEDGER.SAFETY["RESEARCH_ONLY"])
        self.assertTrue(LEDGER.SAFETY["SHADOW_ONLY"])
        self.assertTrue(LEDGER.SAFETY["NOT_APPROVED"])
        self.assertFalse(LEDGER.SAFETY["ENGINE_FEED"])
        self.assertEqual(LEDGER.SAFETY["ORDERS"], 0)
        self.assertEqual(LEDGER.SAFETY["REAL_CAPITAL_BRL"], 0)


if __name__ == "__main__":
    unittest.main()
