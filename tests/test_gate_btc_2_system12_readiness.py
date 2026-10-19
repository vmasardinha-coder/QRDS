import sys
import copy
import json
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gate_btc_2_system12_readiness import assess, retain_replication_progress, REPLICATION_AUTHORITY, REPLICATION_CHECKS


class T(unittest.TestCase):
    def test_missing_or_partial_upstream_cannot_complete_system12(self):
        for report in (None, {"status": "INCONCLUSIVE_ABSTAIN", "system11_complete": False}):
            x = assess(report, None)
            self.assertFalse(x["upstream_system11_ready"])
            self.assertFalse(x["system12_complete"])
            self.assertFalse(x["system13_dependency_released"])
            self.assertEqual(x["scientific_credit"], 0)
            self.assertEqual(x["orders"], 0)

    def test_complete_boolean_without_hash_bound_evidence_is_blocked(self):
        report = {"status": "PASS_FROZEN_LOB_STRESS_REPLAY", "system11_complete": True}
        self.assertEqual(assess(report, None)["status"], "BLOCKED_MISSING_HASH_BOUND_SYSTEM11_LEDGER")
        self.assertEqual(assess(report, [])["status"], "BLOCKED_INVALID_SYSTEM11_EVIDENCE")
        self.assertFalse(assess(report, [])["system12_complete"])


class ReplicationContinuityTests(unittest.TestCase):
    def inputs(self):
        contract = json.loads(REPLICATION_AUTHORITY.read_text())
        receipt = json.loads((REPLICATION_AUTHORITY.parents[2] / "artifacts/gate_btc_2/executive_economic_checkpoint_20261017/SYSTEM12_REPRODUCED.json").read_text())
        structural = {"upstream_system11_ready": True, "status": "STRUCTURAL_READY_PENDING_FROZEN_INDEPENDENT_REPLICATION_CONTRACT",
            "system11_report_sha256": contract["bindings"]["system11_report_semantic_sha256"]}
        return structural, contract, receipt

    def test_completed_parity_points_to_review_without_awarding_credit(self):
        args = self.inputs(); original = copy.deepcopy(args)
        out = retain_replication_progress(*args)
        self.assertEqual(out["status"], "IMPLEMENTATION_PARITY_PASSED_PENDING_INDEPENDENT_ADJUDICATION")
        self.assertEqual(out["frozen_compared_events"], 3307200)
        self.assertEqual(out["frozen_scenario_count"], 300)
        self.assertTrue(out["current_upstream_report_matches_frozen_replication"])
        self.assertFalse(out["system12_complete"])
        self.assertFalse(out["system13_dependency_released"])
        self.assertFalse(out["independent_adjudication_executed"])
        self.assertEqual(out["scientific_credit"], 0)
        self.assertEqual(args, original)

    def test_new_current_report_does_not_inherit_frozen_replication_scope(self):
        structural, contract, receipt = self.inputs()
        structural["system11_report_sha256"] = "different-current-report"
        out = retain_replication_progress(structural, contract, receipt)
        self.assertFalse(out["current_upstream_report_matches_frozen_replication"])
        self.assertEqual(out["replication_scope"], "FROZEN_CONTRACT_ONLY_NO_TRANSFER_TO_NEW_COLLECTION")
        self.assertFalse(out["system12_complete"])

    def test_missing_receipt_keeps_structural_status(self):
        structural, contract, receipt = self.inputs()
        for c, r in [(None, receipt), (contract, None), (None, None)]:
            with self.subTest(contract=c is not None, receipt=r is not None):
                self.assertEqual(retain_replication_progress(structural, c, r)["status"], structural["status"])

    def test_bad_contract_or_bindings_cannot_reuse_parity(self):
        for field in ["contract", "bindings", "contract_sha256"]:
            with self.subTest(field=field):
                s, c, r = self.inputs()
                if field == "contract": c["required_scenario_count"] = 299
                elif field == "bindings": r["bindings"]["dataset_semantic_sha256"] = "wrong"
                else: r["contract_sha256"] = "wrong"
                self.assertEqual(retain_replication_progress(s, c, r)["status"], "BLOCKED_INVALID_FROZEN_REPLICATION_RECEIPT")

    def test_each_failed_check_blocks_completed_parity(self):
        for check in REPLICATION_CHECKS:
            with self.subTest(check=check):
                s, c, r = self.inputs(); r["checks"][check] = False
                self.assertEqual(retain_replication_progress(s, c, r)["status"], "BLOCKED_INVALID_FROZEN_REPLICATION_RECEIPT")

    def test_inconsistent_or_missing_events_fail_closed(self):
        for value in [0, True, -1, 3307199, "3307200", None]:
            with self.subTest(value=value):
                s, c, r = self.inputs(); r["compared_events"] = value
                self.assertEqual(retain_replication_progress(s, c, r)["status"], "BLOCKED_INVALID_FROZEN_REPLICATION_RECEIPT")
        s, c, r = self.inputs(); del r["stressed_execution_results"]
        self.assertEqual(retain_replication_progress(s, c, r)["status"], "BLOCKED_INVALID_FROZEN_REPLICATION_RECEIPT")

    def test_receipt_cannot_self_adjudicate_or_promote(self):
        for key, value in [("system12_complete", True), ("system13_dependency_released", True),
                ("independent_adjudication_executed", True), ("scientific_credit", 1),
                ("orders", 1), ("engine_feed", True), ("economic_claim_authorized", True)]:
            with self.subTest(key=key):
                s, c, r = self.inputs(); r[key] = value
                self.assertEqual(retain_replication_progress(s, c, r)["status"], "BLOCKED_INVALID_FROZEN_REPLICATION_RECEIPT")

    def test_old_frozen_pass_does_not_hide_current_upstream_failure(self):
        s, c, r = self.inputs()
        s.update(upstream_system11_ready=False, status="BLOCKED_INVALID_SYSTEM11_EVIDENCE")
        out = retain_replication_progress(s, c, r)
        self.assertEqual(out["status"], "BLOCKED_INVALID_SYSTEM11_EVIDENCE")
        self.assertTrue(out["frozen_implementation_replication_pass"])
        self.assertFalse(out["system13_dependency_released"])


if __name__ == "__main__":
    unittest.main()

