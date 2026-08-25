import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = (
    ROOT / "tools" / "gate_btc_2_checkpoint7_evidence_inventory_decision_v1.json"
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def file_sha(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class GateBTC2Checkpoint7EvidenceInventoryDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DECISION_PATH.read_text(encoding="utf-8"))

    def test_decision_hash_is_deterministic(self):
        unsigned = dict(self.payload)
        claimed = unsigned.pop("decision_sha256")
        computed = hashlib.sha256(
            json.dumps(
                unsigned,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(claimed, computed)

    def test_bound_implementation_and_report_files_match_exact_hashes(self):
        validation = self.payload["validation"]
        self.assertEqual(
            validation["inventory_tool_sha256"],
            file_sha("tools/gate_btc_2_official_evidence_inventory.py"),
        )
        self.assertEqual(
            validation["inventory_test_file_sha256"],
            file_sha("tests/test_gate_btc_2_official_evidence_inventory.py"),
        )
        self.assertEqual(
            validation["workflow_file_sha256"],
            file_sha(".github/workflows/gate-btc-2-official-evidence-inventory.yml"),
        )
        for claim in self.payload["deep_sweep"]["historical_qrds_claims"]:
            self.assertEqual(claim["report_sha256"], file_sha(claim["report_path"]))

    def test_runtime_inventory_is_exact_but_has_no_admissible_candidate(self):
        inventory = self.payload["physical_inventory"]
        self.assertEqual(
            inventory["status"],
            "BLOCKED_NO_ADMISSIBLE_OFFICIAL_DATASET_CANDIDATE",
        )
        self.assertEqual(inventory["physical_evidence_count"], 25)
        self.assertEqual(inventory["admissible_candidate_count"], 0)
        self.assertEqual(inventory["tabular_discovery"]["tabular_file_count"], 94)
        self.assertEqual(
            inventory["tabular_discovery"]["category_counts"]["unclassified"],
            0,
        )
        self.assertTrue(HEX64.fullmatch(inventory["inventory_sha256"]))
        for commit in self.payload["source_commits"].values():
            self.assertTrue(HEX40.fullmatch(commit))

    def test_manual_v2a_d50_and_qmaster_are_not_relabelled(self):
        sweep = self.payload["deep_sweep"]
        manual = sweep["manual_public_market_data"]
        self.assertEqual(manual["file_count"], 12)
        self.assertEqual(manual["nonempty_file_count"], 9)
        self.assertEqual(manual["empty_file_count"], 3)
        self.assertFalse(manual["observed_availability_timestamp_present"])
        self.assertFalse(manual["formal_schema_bound"])
        self.assertFalse(manual["source_provenance_bound"])
        self.assertEqual(sweep["v2a"]["loaded_symbols"], 95)
        self.assertEqual(sweep["v2a"]["failed_symbols"], 55)
        self.assertTrue(sweep["v2a"]["survivorship_bias_present"])
        self.assertFalse(sweep["d50"]["physical_source_paths_present"])
        self.assertFalse(sweep["qmaster"]["canonical_path_auto_selected"])

    def test_status_claims_cannot_override_the_gate_or_unlock_economics(self):
        for claim in self.payload["deep_sweep"]["historical_qrds_claims"]:
            self.assertIn(
                claim["admission_effect"],
                {
                    "STATUS_ONLY_CANNOT_REPLACE_PHYSICAL_DATASET",
                    "STATUS_ONLY_CANNOT_REPLACE_PHYSICAL_FUNDING_OR_OPEN_INTEREST_BYTES",
                    "SEPARATE_RESEARCH_DECISION_CANNOT_OVERRIDE_GATE_BTC_2_CONTRACT",
                },
            )
        safety = self.payload["safety_boundary"]
        self.assertFalse(safety["official_dataset_descriptor_created"])
        self.assertFalse(safety["official_dataset_sealed"])
        self.assertFalse(safety["economic_calibration_performed"])
        self.assertFalse(safety["engine_feed"])
        self.assertEqual(safety["official_challenger_runs_executed"], 0)
        self.assertEqual(safety["orders_generated"], 0)
        self.assertEqual(safety["real_capital_used"], 0)

    def test_recovery_order_preserves_no_backfill_and_parallel_isolation(self):
        order = self.payload["recovery_order"]
        self.assertIn("WITHOUT_COUNTING_BACKFILL_AS_PROSPECTIVE", order[0])
        self.assertIn("FORWARD_ONLY", order[1])
        self.assertIn("WITHOUT_RETROACTIVE_FILL", order[2])
        self.assertIn("ONLY_AFTER_SEAL", order[-1])
        self.assertFalse(self.payload["contract"]["retrospective_backfill_allowed"])
        self.assertEqual(
            self.payload["isolation"],
            {
                "b3_mutations": 0,
                "delta_mutations": 0,
                "economic_families_released": 0,
                "incumbent_mutations": 0,
                "regime_mutations": 0,
                "runtime_mutations": 0,
            },
        )


if __name__ == "__main__":
    unittest.main()
