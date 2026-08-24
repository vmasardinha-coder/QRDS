import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = ROOT / "tools" / "gate_btc_2_checkpoint6_dataset_contract_decision_v1.json"


def file_sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


class GateBTC2Checkpoint6DatasetContractDecisionTests(unittest.TestCase):
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

    def test_bound_implementation_files_match_exact_hashes(self):
        contract = self.payload["contract_layer"]
        validation = self.payload["validation"]
        self.assertEqual(
            contract["contract_file_sha256"],
            file_sha("tools/gate_btc_2_official_dataset_contract_v1.json"),
        )
        self.assertEqual(
            contract["tool_sha256"],
            file_sha("tools/gate_btc_2_official_dataset_manifest.py"),
        )
        self.assertEqual(
            validation["new_test_file_sha256"],
            file_sha("tests/test_gate_btc_2_official_dataset_manifest.py"),
        )
        self.assertEqual(
            validation["workflow_file_sha256"],
            file_sha(".github/workflows/gate-btc-2-official-dataset-manifest.yml"),
        )

    def test_real_runtime_state_remains_blocked_without_structural_corruption(self):
        readiness = self.payload["current_official_readiness"]
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["hard_failures"], [])
        self.assertEqual(readiness["ready_scopes"], [])
        self.assertEqual(
            readiness["blocked_scopes"],
            ["BTC_CORE", "D50_ECONOMIC", "D50_QUALIFIED", "MULTIASSET_V2A"],
        )
        self.assertIn(
            "V2A_SURVIVORSHIP_BIAS_PRESENT",
            readiness["track_blockers"]["MULTIASSET_V2A"],
        )

    def test_contract_cannot_self_seal_or_unlock_economics(self):
        self.assertEqual(
            self.payload["decision"],
            "BLOCKED_OFFICIAL_DATASET_EVIDENCE_NOT_READY",
        )
        self.assertEqual(
            self.payload["implementation_status"],
            "OFFICIAL_DATASET_ADMISSION_CONTRACT_READY",
        )
        safety = self.payload["safety_boundary"]
        self.assertFalse(safety["official_dataset_sealed"])
        self.assertFalse(safety["official_challenger_runs_allowed"])
        self.assertFalse(safety["economic_calibration_allowed"])
        self.assertFalse(safety["engine_feed"])
        self.assertEqual(safety["orders_generated"], 0)
        self.assertEqual(safety["real_capital_used"], 0)

    def test_delta_regime_b3_incumbents_and_runtime_are_isolated(self):
        isolation = self.payload["isolation"]
        self.assertEqual(
            isolation,
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
