import hashlib
import json
import re
import unittest
from pathlib import Path


class GateBTC2Item2Checkpoint4DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo = Path(__file__).resolve().parents[1]
        cls.path = repo / "tools/gate_btc_2_item2_checkpoint4_decision_v1.json"
        cls.payload = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_decision_is_blocked_without_relabeling_synthetic_pass(self):
        p = self.payload
        self.assertEqual(p["checkpoint"], 4)
        self.assertEqual(p["roadmap_item"], 2)
        self.assertEqual(p["decision"], "BLOCKED_OFFICIAL_EVIDENCE_NOT_READY")
        self.assertEqual(
            p["implementation_status"],
            "CONTRACTS_CONFORMANT_OFFICIAL_VALIDATION_BLOCKED",
        )
        self.assertEqual(p["temporal_causality"]["status"], "PASS_SYNTHETIC_CONFORMANCE_ONLY")
        self.assertFalse(p["temporal_causality"]["official_dataset_audited"])
        self.assertFalse(p["temporal_causality"]["stage_5_core_audits_passed"])

    def test_readiness_preserves_every_blocked_scope_and_no_hard_failure(self):
        readiness = self.payload["dataset_readiness"]
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["hard_failures"], [])
        self.assertEqual(readiness["ready_scopes"], [])
        self.assertEqual(
            set(readiness["blocked_scopes"]),
            {"BTC_CORE", "D50_ECONOMIC", "D50_QUALIFIED", "MULTIASSET_V2A"},
        )
        blockers = readiness["track_blockers"]
        self.assertIn("D50_SYNCHRONIZED_FAILURE_ACTIVE", blockers["D50_QUALIFIED"])
        self.assertIn("V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE", blockers["MULTIASSET_V2A"])
        self.assertIn("V2A_SURVIVORSHIP_BIAS_PRESENT", blockers["MULTIASSET_V2A"])

    def test_provenance_repair_changed_only_reporting_sidecars(self):
        repair = self.payload["reporting_provenance_repair"]
        self.assertEqual(repair["source_ledgers_mutated"], 0)
        self.assertEqual(repair["exact_source_hash_checks"], 12)
        self.assertFalse(repair["health_classification_changed"])
        self.assertEqual(
            set(repair["changed_files"]),
            {
                "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
                "runtime/GATE_BTC_HEALTH_DIMENSIONS.json",
            },
        )

    def test_all_evidence_and_commit_hashes_are_well_formed(self):
        hex64 = re.compile(r"^[0-9a-f]{64}$")
        hex40 = re.compile(r"^[0-9a-f]{40}$")
        for commit in self.payload["source_commits"].values():
            self.assertRegex(commit, hex40)
        readiness = self.payload["dataset_readiness"]
        self.assertRegex(readiness["assessment_sha256"], hex64)
        self.assertRegex(readiness["source_manifest_sha256"], hex64)
        for source in readiness["source_manifest"].values():
            self.assertRegex(source["sha256"], hex64)
            self.assertGreater(source["byte_length"], 0)
        temporal = self.payload["temporal_causality"]
        for key in ("foundation_contract_sha256", "trace_sha256", "audit_sha256"):
            self.assertRegex(temporal[key], hex64)

    def test_safety_boundary_remains_zero_and_not_approved(self):
        safety = self.payload["safety_boundary"]
        self.assertTrue(safety["research_only"])
        self.assertTrue(safety["shadow_only"])
        self.assertTrue(safety["not_approved"])
        self.assertFalse(safety["engine_feed"])
        self.assertFalse(safety["promotion_allowed"])
        self.assertFalse(safety["official_challenger_runs_allowed"])
        self.assertFalse(safety["dataset_sealed"])
        self.assertEqual(safety["orders_generated"], 0)
        self.assertEqual(safety["real_capital_used"], 0)
        self.assertEqual(safety["methodology_changes"], 0)
        self.assertEqual(safety["source_ledger_mutations"], 0)

    def test_decision_hash_is_deterministic(self):
        unsigned = dict(self.payload)
        observed = unsigned.pop("decision_sha256")
        raw = json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), observed)


if __name__ == "__main__":
    unittest.main()
