import copy
import json
from pathlib import Path
import tempfile
import unittest
import tests.test_gate_btc_2_system12_adjudication_reporting as legacy
from gate_btc_system12_post_review_release import RELEASE_AUTHORITY, retain_post_review_release
from tools.gate_btc_reporting_authority import system12_summary


class PostReviewReleaseTests(unittest.TestCase):
    def inputs(self):
        base, contract, review = legacy.AdjudicationReportingTests().inputs()
        readiness = legacy.retain_adjudication_progress(base, contract, review)
        readiness["schema"] = "gate_btc.2_0.system12_readiness.v1"
        release = json.loads(RELEASE_AUTHORITY.read_text(encoding="utf-8"))
        return readiness, contract, review, release

    def test_authorized_frozen_parity_releases_research_dependency_only(self):
        args = self.inputs(); before = copy.deepcopy(args)
        out = retain_post_review_release(*args)
        self.assertTrue(out["system12_complete"])
        self.assertTrue(out["system13_dependency_released"])
        self.assertFalse(out["system13_complete"])
        for key in ("engine_feed", "automatic_promotion", "economic_claim_authorized"):
            self.assertIs(out[key], False)
        for key in ("scientific_credit", "orders", "real_capital_brl"):
            self.assertEqual(out[key], 0)
        self.assertEqual(args, before)

    def test_absent_or_unapproved_release_cannot_complete(self):
        args = list(self.inputs())
        args[-1] = None
        self.assertFalse(retain_post_review_release(*args)["system12_complete"])
        args = list(self.inputs()); args[-1]["authorized"] = False
        self.assertEqual(retain_post_review_release(*args)["post_review_release_status"], "INVALID")
        self.assertFalse(retain_post_review_release(*args)["system13_dependency_released"])

    def test_changed_subject_review_or_release_rejected(self):
        for subject in ("contract", "review", "release"):
            with self.subTest(subject=subject):
                args = list(self.inputs())
                if subject == "contract": args[1]["bindings"]["dataset_semantic_sha256"] = "changed"
                if subject == "review": args[2]["decision"] = "FAIL"
                if subject == "release": args[3]["research_effect"]["orders"] = 1
                out = retain_post_review_release(*args)
                self.assertEqual(out["post_review_release_status"], "INVALID")
                self.assertFalse(out["system12_complete"])

    def test_review_or_replication_missing_blocks_even_with_authorization(self):
        for key, value in (("independent_adjudication_executed", False),
                           ("replication_continuity_status", "INVALID")):
            args = list(self.inputs()); args[0][key] = value
            self.assertFalse(retain_post_review_release(*args)["system13_dependency_released"])

    def test_current_upstream_failure_remains_blocked(self):
        args = list(self.inputs())
        args[0].update(upstream_system11_ready=False, status="BLOCKED_INVALID_SYSTEM11_EVIDENCE")
        out = retain_post_review_release(*args)
        self.assertFalse(out["system12_complete"])
        self.assertFalse(out["system13_dependency_released"])
        self.assertEqual(out["status"], "BLOCKED_INVALID_SYSTEM11_EVIDENCE")

    def test_factory_projects_the_same_bound_release_without_writing_inputs(self):
        args = self.inputs()
        readiness = retain_post_review_release(*args)
        _, _, implementation = legacy.legacy.ReplicationContinuityTests().inputs()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for name, data in (("READINESS.json", readiness),
                ("IMPLEMENTATION_REPLICATION_CONTRACT.json", args[1]),
                ("IMPLEMENTATION_REPLICATION.json", implementation)):
                (root / name).write_text(json.dumps(data), encoding="utf-8")
            before = {p: p.read_bytes() for p in root.iterdir()}
            out = system12_summary(root)
            self.assertEqual(out["status"], readiness["status"])
            self.assertTrue(out["system13_dependency_released"])
            self.assertFalse(out["system13_complete"])
            self.assertEqual(before, {p: p.read_bytes() for p in root.iterdir()})
            readiness["post_review_release_semantic_sha256"] = "changed"
            (root / "READINESS.json").write_text(json.dumps(readiness), encoding="utf-8")
            self.assertFalse(system12_summary(root)["system13_dependency_released"])


if __name__ == "__main__":
    unittest.main()
