import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "tools" / "gate_btc_b3_h120_h129_result.json"
LEDGER = ROOT / "tools" / "gate_btc_b3_h120_h129_result_ledger.jsonl"
FACTORY = ROOT / "tools" / "gate_btc_research_factory_status.json"


class H120H129ResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.ledger_bytes = LEDGER.read_bytes()
        cls.ledger = [
            json.loads(line)
            for line in cls.ledger_bytes.decode("utf-8").splitlines()
            if line.strip()
        ]
        cls.factory = json.loads(FACTORY.read_text(encoding="utf-8"))

    def test_audited_evidence_is_pinned(self):
        evidence = self.result["evidence"]
        self.assertEqual(evidence["execution_pr"], 207)
        self.assertEqual(evidence["workflow_run_id"], 32916684473)
        self.assertEqual(evidence["artifact_id"], 9588840057)
        self.assertEqual(
            evidence["merge_commit"],
            "efa69653dc14ec6577fde0fae4a7c8222c82f544",
        )
        self.assertEqual(
            evidence["files_sha256"]["result_ledger"],
            hashlib.sha256(self.ledger_bytes).hexdigest(),
        )
        self.assertEqual(self.result["source_qa"]["passed"], 9)
        self.assertEqual(self.result["source_qa"]["total"], 9)
        self.assertEqual(self.result["ingestion"]["requested_days"], 1154)
        self.assertEqual(self.result["ingestion"]["pass_days"], 1152)
        self.assertEqual(len(self.result["ingestion"]["data_gaps"]), 2)

    def test_null_result_and_family_ledger_agree(self):
        expected_states = self.result["states"]
        by_family = {row["family"]: row for row in self.ledger}
        self.assertEqual(len(self.ledger), 10)
        self.assertEqual(set(by_family), set(expected_states))
        self.assertEqual(
            {family: row["state"] for family, row in by_family.items()},
            expected_states,
        )
        self.assertEqual(
            sorted(
                family
                for family, row in by_family.items()
                if row["discovery"]["survives"]
            ),
            self.result["discovery_survivor_families"],
        )
        self.assertEqual(
            sorted(
                family
                for family, row in by_family.items()
                if row["replication"]["survives"]
            ),
            self.result["replication_survivor_families"],
        )
        self.assertEqual(
            sum(row["discovery"]["qualified_cells"] for row in self.ledger),
            self.result["qualified_cells"]["discovery"],
        )
        self.assertEqual(
            sum(row["replication"]["qualified_cells"] for row in self.ledger),
            self.result["qualified_cells"]["replication"],
        )
        self.assertEqual(self.result["survivors"], [])
        self.assertEqual(self.result["data_gap_families"], [])

    def test_safety_boundary_is_exact(self):
        self.assertFalse(self.result["h1_economics_read"])
        self.assertFalse(self.result["survivor_partial_economics_read"])
        self.assertEqual(self.result["orders"], 0)
        self.assertEqual(self.result["capital"], 0)
        self.assertFalse(self.result["engine_feed"])
        self.assertTrue(self.result["not_approved"])
        for row in self.ledger:
            self.assertEqual(row["orders"], 0)
            self.assertEqual(row["capital"], 0)
            self.assertFalse(row["engine_feed"])
            self.assertTrue(row["not_approved"])

    def test_factory_points_to_the_closed_generation(self):
        track = self.factory["tracks"]["B3_H40_PLUS"]
        self.assertGreaterEqual(
            self.factory["generated_at_utc"],
            self.result["recorded_at_utc"],
        )
        self.assertEqual(track["classification"], "OPEN_DISCOVERY")
        self.assertIn("H120_H129_CLOSED_NO_SURVIVOR", track["status"])
        self.assertTrue(track["status"].endswith("H130_H139_ISSUE_210_SOURCE_QA_READY"))
        self.assertEqual(track["closed_generation_issue"], 205)
        self.assertEqual(track["closed_generation_pr"], 207)
        self.assertEqual(track["open_issue"], 210)
        self.assertIsNone(track["open_pr"])
        self.assertEqual(track["latest_merged_pr"], 211)
        self.assertEqual(track["source_qa_workflow_run"], 32926619387)
        self.assertEqual(track["source_qa_artifact"], 9591754804)
        self.assertIn("H130-H139", track["action"])
        self.assertEqual(self.factory["safety"]["orders"], 0)
        self.assertEqual(self.factory["safety"]["real_capital"], 0)
        self.assertFalse(self.factory["safety"]["engine_feed"])


if __name__ == "__main__":
    unittest.main()
