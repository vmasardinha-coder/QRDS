import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = (
    ROOT / "tools" / "gate_btc_2_checkpoint8_source_admission_decision_v1.json"
)
CP7_DECISION_PATH = (
    ROOT / "tools" / "gate_btc_2_checkpoint7_evidence_inventory_decision_v1.json"
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def file_hash(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


class GateBTC2Checkpoint8SourceAdmissionDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DECISION_PATH.read_text(encoding="utf-8"))
        cls.cp7 = json.loads(CP7_DECISION_PATH.read_text(encoding="utf-8"))

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

    def test_contract_implementation_tests_and_workflow_are_exactly_bound(self):
        contract = self.payload["adapter_contract"]
        validation = self.payload["validation"]
        self.assertEqual(
            contract["contract_file_sha256"],
            file_hash("tools/gate_btc_2_source_admission_contract_v1.json"),
        )
        self.assertEqual(
            validation["source_admission_tool_sha256"],
            file_hash("tools/gate_btc_2_source_admission.py"),
        )
        self.assertEqual(
            validation["source_admission_test_file_sha256"],
            file_hash("tests/test_gate_btc_2_source_admission.py"),
        )
        self.assertEqual(
            validation["workflow_file_sha256"],
            file_hash(".github/workflows/gate-btc-2-source-admission.yml"),
        )

    def test_current_source_state_remains_exactly_blocked(self):
        current = self.payload["current_preflight"]
        self.assertEqual(
            current["status"], "BLOCKED_SOURCE_ADMISSION_NO_COMPLETE_BUNDLE"
        )
        self.assertEqual(current["complete_role_count"], 0)
        self.assertEqual(current["admissible_source_bundle_count"], 0)
        self.assertEqual(current["recoverable_manual_btc_ohlc_count"], 3)
        self.assertEqual(
            current["exact_physical_hash_matches"], {"FUNDING": [], "OHLC": []}
        )
        self.assertTrue(HEX64.fullmatch(current["preflight_sha256"]))
        self.assertFalse(current["source_admitted"])
        self.assertFalse(current["official_dataset_sealed"])
        self.assertFalse(current["economics_allowed"])
        self.assertEqual(current["prospective_rows_credited"], 0)

    def test_hash_recovery_claims_match_checkpoint7_physical_inventory(self):
        recovery = self.payload["hash_claim_recovery_sweep"]
        cp7_d50 = self.cp7["deep_sweep"]["d50"]
        self.assertEqual(
            recovery["current_claims"]["ohlc"],
            cp7_d50["ohlc_source_sha256_claim"],
        )
        self.assertEqual(
            recovery["current_claims"]["funding"],
            cp7_d50["funding_source_sha256_claim"],
        )
        self.assertFalse(cp7_d50["physical_source_paths_present"])
        self.assertEqual(self.cp7["physical_inventory"]["admissible_candidate_count"], 0)
        self.assertEqual(recovery["current_runtime_physical_matches"], {"funding": [], "ohlc": []})
        self.assertFalse(recovery["status_only_claim_can_admit_source"])
        self.assertTrue(HEX40.fullmatch(recovery["first_current_claim_commit"]))
        self.assertTrue(HEX40.fullmatch(recovery["first_current_claim_commit_parent"]))
        self.assertTrue(
            HEX64.fullmatch(recovery["referenced_external_report"]["sha256_claim"])
        )
        self.assertFalse(
            recovery["referenced_external_report"]["physically_present_at_runtime_commit"]
        )

    def test_adapter_covers_causality_full_roles_and_no_backfill(self):
        guards = set(self.payload["adapter_guards"])
        self.assertIn("EXACT_SOURCE_BYTES_SHA256_REQUIRED", guards)
        self.assertIn("D50_STATUS_CLAIM_MUST_MATCH_PHYSICAL_BYTES", guards)
        self.assertIn("OHLC_AND_FUNDING_BOTH_REQUIRED_NO_PARTIAL_ADMISSION", guards)
        self.assertIn("PROVIDER_AVAILABILITY_TIMESTAMP_MAY_NOT_BE_INVENTED", guards)
        self.assertIn("UNCONFIRMED_ROWS_PROHIBITED", guards)
        self.assertIn("FUNDING_MAY_NOT_BE_INFERRED_FROM_OHLC", guards)
        self.assertIn("RECOVERED_HISTORICAL_BYTES_RECEIVE_ZERO_PROSPECTIVE_CREDIT", guards)
        boundary = self.payload["outcome_boundary"]
        self.assertEqual(
            boundary["complete_fixture_result"],
            "READY_FOR_EXPLICIT_SOURCE_ADMISSION_REVIEW",
        )
        self.assertFalse(boundary["complete_fixture_source_admitted"])
        self.assertFalse(boundary["stage_3_dataset_sealed"])

    def test_safety_and_parallel_isolation_remain_locked(self):
        safety = self.payload["safety_boundary"]
        self.assertTrue(safety["research_only"])
        self.assertTrue(safety["shadow_only"])
        self.assertTrue(safety["not_approved"])
        self.assertFalse(safety["engine_feed"])
        self.assertFalse(safety["source_admitted"])
        self.assertFalse(safety["official_dataset_sealed"])
        self.assertFalse(safety["economic_calibration_performed"])
        self.assertEqual(safety["prospective_rows_credited"], 0)
        self.assertEqual(safety["historical_rows_backfilled"], 0)
        self.assertEqual(safety["orders_generated"], 0)
        self.assertEqual(safety["real_capital_used"], 0)
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
        for commit in self.payload["source_commits"].values():
            self.assertTrue(HEX40.fullmatch(commit))


if __name__ == "__main__":
    unittest.main()
