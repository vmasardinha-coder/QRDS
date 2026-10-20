import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import tests.test_gate_btc_2_system12_adjudication_reporting as review_tests
from tools.gate_btc_reporting_authority import system12_summary
from tools.gate_btc_factory_status_export import export_tracks


class System12FactoryProjectionTests(unittest.TestCase):
    def inputs(self):
        result, contract, review = review_tests.AdjudicationReportingTests().inputs()
        readiness = review_tests.retain_adjudication_progress(result, contract, review)
        readiness["schema"] = "gate_btc.2_0.system12_readiness.v1"
        _, _, implementation = review_tests.legacy.ReplicationContinuityTests().inputs()
        return contract, implementation, readiness

    def write(self, root, values):
        for name, value in zip(("IMPLEMENTATION_REPLICATION_CONTRACT.json",
                "IMPLEMENTATION_REPLICATION.json", "READINESS.json"), values):
            (root / name).write_text(json.dumps(value), encoding="utf-8")

    def test_export_retains_adjudication_and_formal_release_boundary_without_writes(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            root = repo / "runtime/gate_btc_2/system12"
            root.mkdir(parents=True)
            self.write(root, self.inputs())
            before = {p: p.read_bytes() for p in root.glob("*")}
            out = export_tracks(repo)["system12"]["data"]
            self.assertEqual(out["status"], "FROZEN_PARITY_ADJUDICATED_PENDING_FORMAL_RELEASE")
            self.assertTrue(out["independent_adjudication_executed"])
            self.assertEqual(out["next_action"], "BIND_EXPLICIT_POST_REVIEW_RELEASE_WITHOUT_REFREEZE")
            for key in ("system12_complete", "system13_dependency_released", "scientific_authority"):
                self.assertIs(out[key], False)
            self.assertEqual(out["scientific_credit"], 0)
            self.assertIn("pinned_adjudication", out["source_sha256"])
            self.assertEqual(before, {p: p.read_bytes() for p in root.glob("*")})

    def test_missing_readiness_retains_pre_review_stage(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.write(root, self.inputs())
            (root / "READINESS.json").unlink()
            out = system12_summary(root)
            self.assertFalse(out["independent_adjudication_executed"])

    def test_wrong_binding_pin_or_operational_release_never_claims_review(self):
        for key, value in (
            ("adjudication_receipt_semantic_sha256", "wrong"),
            ("adjudicated_bindings", {}),
            ("frozen_replication_contract_sha256", "wrong"),
            ("system13_dependency_released", True),
            ("system12_complete", True),
            ("orders", 1),
            ("scientific_credit", True)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as td:
                values = self.inputs(); values[2][key] = value
                root = Path(td); self.write(root, values)
                self.assertFalse(system12_summary(root)["independent_adjudication_executed"])

    def test_readiness_cannot_override_invalid_implementation(self):
        with tempfile.TemporaryDirectory() as td:
            values = self.inputs(); values[1]["checks"]["event_parity"] = False
            root = Path(td); self.write(root, values)
            out = system12_summary(root)
            self.assertFalse(out["implementation_replication_pass"])
            self.assertFalse(out["independent_adjudication_executed"])

    def test_frozen_review_does_not_hide_current_upstream_failure(self):
        with tempfile.TemporaryDirectory() as td:
            values = self.inputs()
            values[2].update(upstream_system11_ready=False, status="BLOCKED_INVALID_SYSTEM11_EVIDENCE")
            root = Path(td); self.write(root, values)
            out = system12_summary(root)
            self.assertTrue(out["independent_adjudication_executed"])
            self.assertEqual(out["status"], "BLOCKED_CURRENT_READINESS_WITH_FROZEN_ADJUDICATION_RETAINED")

    def test_changed_pinned_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.write(root, self.inputs())
            original = Path.read_text
            def tamper(path, *args, **kwargs):
                text = original(path, *args, **kwargs)
                if path.name == "SISTEMA12_PARECER.json":
                    obj = json.loads(text); obj["decision"] = "FAIL"
                    return json.dumps(obj)
                return text
            with patch.object(Path, "read_text", tamper):
                self.assertFalse(system12_summary(root)["independent_adjudication_executed"])


if __name__ == "__main__":
    unittest.main()
