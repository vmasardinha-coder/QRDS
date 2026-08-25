from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLANNER = ROOT / "tools" / "gate_btc_factory" / "plan_factory_transitions.py"
APPLIER = ROOT / "tools" / "gate_btc_factory" / "apply_factory_transitions.py"
RUNNER = ROOT / "tools" / "gate_btc_factory" / "run_factory_ci.py"
WORKFLOW = ROOT / ".github" / "workflows" / "gate-btc-factory-shadow.yml"
FLOW_CONTRACT = ROOT / "tools" / "gate_btc_factory" / "FAMILY_FLOW_CONTRACT.v1.json"
WORKFLOW_CONTRACT = ROOT / "tools" / "gate_btc_factory" / "WORKFLOW_CONTRACT.v1.json"

RUNTIME_SAFETY = {
    "ENGINE_FEED": False,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
}
PLAN_SAFETY = {
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "production_activation_allowed": False,
}


def load_module(name: str, path: Path):
    module_dir = str(path.parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def source() -> dict:
    return {
        "generated_at_utc": "2026-08-25T10:05:49Z",
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
            "no_holdout_contamination": True,
        },
        "tracks": {
            "B3_H40_PLUS": {
                "classification": "OPEN_DISCOVERY",
                "status": "H120_H129_CLOSED_NULL",
                "open_issue": None,
                "open_pr": None,
            },
            "B3_H31": {
                "classification": "SURVIVOR_MONITORING",
                "status": "APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING",
            },
        },
    }


def runtime(freshness: str) -> dict:
    return {
        "global_safety": RUNTIME_SAFETY,
        "source_generated_at": "2026-08-25T10:05:49Z",
        "source_hash": "a" * 64,
        "source_freshness": {
            "status": freshness,
            "freshness_limit_minutes": 180,
            "future_timestamp_tolerance_minutes": 5,
        },
    }


class FactoryStaleReadOnlyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.planner = load_module("factory_transition_planner", PLANNER)
        cls.runner = load_module("factory_ci_runner", RUNNER)

    def test_stale_source_emits_zero_action_read_only_plan(self):
        plan = self.planner.build_plan(
            source(),
            runtime("STALE_READ_ONLY"),
            now=datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(plan["transitions_allowed"])
        self.assertEqual(plan["source_freshness"], "STALE_READ_ONLY")
        self.assertEqual(plan["blocked_reason"], "STALE_SOURCE_READ_ONLY_NO_TRANSITIONS")
        self.assertEqual(plan["actions"], [])
        self.assertEqual(plan["safety"], PLAN_SAFETY)

    def test_fresh_source_can_plan_closed_generation_and_explicit_approval(self):
        plan = self.planner.build_plan(
            source(),
            runtime("FRESH"),
            now=datetime(2026, 8, 25, 11, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(plan["transitions_allowed"])
        self.assertIsNone(plan["blocked_reason"])
        self.assertEqual(
            [row["action"] for row in plan["actions"]],
            ["CREATE_NEXT_GENERATION_ISSUE", "ACTIVATE_APPROVED_PROSPECTIVE_SHADOW"],
        )
        self.assertEqual(plan["actions"][0]["marker"], "B3 H130-H139")
        self.assertEqual(plan["actions"][1]["track"], "B3_H31")

    def test_open_issue_blocks_next_generation_even_when_status_says_closed(self):
        src = source()
        src["tracks"]["B3_H40_PLUS"]["open_issue"] = 206
        plan = self.planner.build_plan(
            src,
            runtime("FRESH"),
            now=datetime(2026, 8, 25, 11, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            [row["action"] for row in plan["actions"]],
            ["ACTIVATE_APPROVED_PROSPECTIVE_SHADOW"],
        )

    def test_runtime_must_match_current_source_timestamp(self):
        observed = runtime("FRESH")
        observed["source_generated_at"] = "2026-08-24T10:05:49Z"
        with self.assertRaisesRegex(SystemExit, "canonical source timestamp"):
            self.planner.build_plan(
                source(),
                observed,
                now=datetime(2026, 8, 25, 11, 0, tzinfo=timezone.utc),
            )

    def test_runtime_cannot_claim_fresh_after_source_age_limit(self):
        with self.assertRaisesRegex(SystemExit, "does not match canonical source age"):
            self.planner.build_plan(
                source(),
                runtime("FRESH"),
                now=datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc),
            )

    def test_runtime_must_match_current_source_hash(self):
        with self.assertRaisesRegex(SystemExit, "canonical source hash"):
            self.planner.build_plan(
                source(),
                runtime("FRESH"),
                source_hash="b" * 64,
                now=datetime(2026, 8, 25, 11, 0, tzinfo=timezone.utc),
            )

    def test_materially_future_source_timestamp_fails_closed(self):
        with self.assertRaisesRegex(SystemExit, "materially in the future"):
            self.planner.build_plan(
                source(),
                runtime("FRESH"),
                now=datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
            )

    def test_ci_runner_rejects_materially_future_source_timestamp(self):
        with self.assertRaisesRegex(SystemExit, "materially in the future"):
            self.runner.age_minutes(
                datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
                datetime(2026, 8, 25, 10, 5, tzinfo=timezone.utc),
            )

    def test_stale_applier_is_noop_without_token_or_registry_mutation(self):
        applier = load_module("factory_transition_applier_noop", APPLIER)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plan_path = base / "plan.json"
            registry_path = base / "registry.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "source_freshness": "STALE_READ_ONLY",
                        "transitions_allowed": False,
                        "actions": [],
                        "safety": PLAN_SAFETY,
                    }
                ),
                encoding="utf-8",
            )
            registry = {"schema": "test", "activations": {"KEEP": {"state": "UNCHANGED"}}}
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            applier.PLAN = plan_path
            applier.REGISTRY = registry_path
            self.assertEqual(applier.main(), 0)
            self.assertEqual(json.loads(registry_path.read_text(encoding="utf-8")), registry)

    def test_stale_plan_with_action_fails_closed(self):
        applier = load_module("factory_transition_applier_reject", APPLIER)
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plan_path = base / "plan.json"
            registry_path = base / "registry.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "source_freshness": "STALE_READ_ONLY",
                        "transitions_allowed": False,
                        "actions": [{"action": "CREATE_NEXT_GENERATION_ISSUE"}],
                        "safety": PLAN_SAFETY,
                    }
                ),
                encoding="utf-8",
            )
            registry_path.write_text(json.dumps({"activations": {}}), encoding="utf-8")
            applier.PLAN = plan_path
            applier.REGISTRY = registry_path
            with self.assertRaisesRegex(SystemExit, "stale source produced transition actions"):
                applier.main()

    def test_fresh_plan_keeps_issue_creation_and_shadow_registry_path(self):
        applier = load_module("factory_transition_applier_fresh", APPLIER)
        calls: list[tuple[str, ...]] = []

        def fake_gh(*args: str) -> str:
            calls.append(args)
            return "[]" if args[:2] == ("issue", "list") else "123"

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            plan_path = base / "plan.json"
            registry_path = base / "registry.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "source_freshness": "FRESH",
                        "transitions_allowed": True,
                        "actions": [
                            {
                                "action": "ACTIVATE_APPROVED_PROSPECTIVE_SHADOW",
                                "track": "B3_H31",
                                "status": "APPROVED_FOR_SEPARATE_PROSPECTIVE_SOURCE_BINDING",
                                "marker": "AUTO-PROSPECTIVE:B3_H31",
                                "activation_state": "ACTIVE_PROSPECTIVE_SHADOW",
                            }
                        ],
                        "safety": PLAN_SAFETY,
                    }
                ),
                encoding="utf-8",
            )
            registry_path.write_text(
                json.dumps({"schema": "test", "activations": {}}),
                encoding="utf-8",
            )
            applier.PLAN = plan_path
            applier.REGISTRY = registry_path
            applier.gh = fake_gh
            self.assertEqual(applier.main(), 0)
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            activation = registry["activations"]["B3_H31"]
            self.assertEqual(activation["state"], "ACTIVE_PROSPECTIVE_SHADOW")
            self.assertEqual(activation["orders"], 0)
            self.assertEqual(activation["real_capital"], 0)
            self.assertFalse(activation["engine_feed"])
            self.assertTrue(any(row[:2] == ("issue", "create") for row in calls))

    def test_workflow_and_contracts_publish_stale_artifact_without_transition(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("cycle continues read-only with zero transitions", workflow)
        self.assertNotIn("FAIL stale factory source cannot drive automatic transitions", workflow)
        flow = json.loads(FLOW_CONTRACT.read_text(encoding="utf-8"))
        contract = json.loads(WORKFLOW_CONTRACT.read_text(encoding="utf-8"))
        expected = "SUCCESSFUL_READ_ONLY_NOOP_WITH_ARTIFACT_AND_WARNING"
        self.assertEqual(flow["freshness_policy"]["stale_cycle_behavior"], expected)
        self.assertEqual(contract["stale_runtime_behavior"], expected)
        self.assertEqual(flow["freshness_policy"]["future_timestamp_tolerance_minutes"], 5)
        self.assertEqual(contract["future_timestamp_tolerance_minutes"], 5)


if __name__ == "__main__":
    unittest.main()
