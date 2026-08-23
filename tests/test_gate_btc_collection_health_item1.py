import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from tools.gate_btc_health_dimensions import build, classify_component
from tools.gate_btc_reporting_operational_overlay import enrich


SAFE = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "orders_generated": 0,
    "real_capital_used": 0,
}


def base_state(reference="2026-08-22"):
    return {
        **SAFE,
        "reference_data_date": reference,
        "delivery_complete": True,
        "status": "PASS",
        "components": {},
        "warnings": {
            "stale_components": [],
            "missing_or_undated_components": [],
        },
    }


class CollectionHealthItem1Test(unittest.TestCase):
    def write_status(self, root, relative, payload):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_b3_h1_friday_is_fresh_for_saturday_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_status(root, "ledgers/b3_h1/STATUS.json", {
                **SAFE,
                "schema": "gate_btc.b3.h1.runtime_ledger.v1",
                "status": "ACTIVE_STRUCTURAL_COLLECTION",
                "latest_valid_date": "2026-08-21",
                "valid_observation_count": 1,
                "economics_locked": True,
                "backfill_automatically_created": False,
            })
            result = enrich(root, base_state("2026-08-22"))
            b3 = result["components"]["b3_h1"]
            self.assertEqual(b3["freshness"], "FRESH")
            self.assertEqual(b3["expected_session_weekday_proxy"], "2026-08-21")
            self.assertEqual(result["sources"]["b3_h1"]["schema"], "gate_btc.b3.h1.runtime_ledger.v1")
            self.assertEqual(len(result["sources"]["b3_h1"]["sha256"]), 64)

    def test_fresh_momentum_failure_is_red_and_blocks_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_status(root, "ledgers/momentum_m1_m2/STATUS.json", {
                **SAFE,
                "engine_feed": False,
                "promotion_allowed": False,
                "data_as_of": "2026-08-23",
                "status": "OPEN_DIAGNOSTIC_COLLECTION_DELIVERY",
                "last_run_state": "FAILED_RUN_SEEN_ON_MAIN_ROOT_CAUSE_NOT_YET_PROVEN",
                "methodology_failure": False,
            })
            result = enrich(root, base_state("2026-08-23"))
            momentum = result["components"]["momentum_m1_m2"]
            self.assertEqual(momentum["freshness"], "FRESH")
            self.assertEqual(momentum["collection_health_hint"], "RED_FAILED_DELIVERY")
            self.assertIn("momentum_m1_m2", result["warnings"]["failed_delivery_components"])
            self.assertFalse(result["delivery_complete"])

    def test_fresh_v16b_blocked_signal_producer_is_amber(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write_status(root, "ledgers/v16b/STATUS.json", {
                **SAFE,
                "engine_feed": False,
                "promotion_allowed": False,
                "data_as_of": "2026-08-23",
                "status": "WAITING_NEXT_CANONICAL_WINDOW",
                "signal_producer": "BLOCKED_UNTIL_FRESH_CAUSAL_FEATURE_PANEL_MAPPING_IS_VERIFIED",
            })
            result = enrich(root, base_state("2026-08-23"))
            v16b = result["components"]["v16b"]
            self.assertEqual(v16b["freshness"], "FRESH")
            self.assertEqual(v16b["collection_health_hint"], "AMBER_BLOCKED_DEPENDENCY")
            self.assertIn("v16b", result["warnings"]["blocked_dependency_components"])
            self.assertFalse(result["delivery_complete"])

    def test_health_dimensions_never_promote_failure_or_block_to_green(self):
        report = {
            **base_state("2026-08-23"),
            "delivery_complete": False,
            "components": {
                "momentum_m1_m2": {
                    "status": "OPEN_DIAGNOSTIC_COLLECTION_DELIVERY",
                    "freshness": "FRESH",
                    "last_run_state": "FAILED_RUN_SEEN_ON_MAIN",
                    "collection_health_hint": "RED_FAILED_DELIVERY",
                },
                "v16b": {
                    "status": "WAITING_NEXT_CANONICAL_WINDOW",
                    "freshness": "FRESH",
                    "collection_health_hint": "AMBER_BLOCKED_DEPENDENCY",
                },
            },
        }
        health = build(report)
        self.assertEqual(health["collection_delivery"], "RED_INCOMPLETE_DELIVERY")
        self.assertEqual(health["components"]["momentum_m1_m2"]["collection_health"], "RED_FAILED_DELIVERY")
        self.assertEqual(health["components"]["v16b"]["collection_health"], "AMBER_BLOCKED_DEPENDENCY")
        self.assertEqual(health["operational_authorization"], "NOT_APPROVED")

    def test_stale_precedes_any_green_hint(self):
        result = classify_component("x", {
            "status": "ACTIVE",
            "freshness": "STALE",
            "collection_health_hint": "GREEN",
        })
        self.assertEqual(result["collection_health"], "RED_STALE")

    def test_closeout_keeps_all_safety_locks(self):
        repo = Path(__file__).resolve().parents[1]
        closeout = json.loads((repo / "tools/gate_btc_collection_health_item1_closeout_v1.json").read_text(encoding="utf-8"))
        self.assertEqual(closeout["implementation_status"], "CLOSED_IMPLEMENTED_FAIL_CLOSED")
        self.assertEqual(closeout["live_delivery_status"], "DYNAMIC_NOT_FORCED_GREEN")
        self.assertTrue({"b3_h1", "v16b", "momentum_m1_m2"}.issubset(closeout["required_component_coverage"]))
        self.assertEqual(closeout["safety_boundary"]["orders_generated"], 0)
        self.assertEqual(closeout["safety_boundary"]["real_capital_used"], 0)
        self.assertFalse(closeout["safety_boundary"]["h1_economics_changed"])


if __name__ == "__main__":
    unittest.main()
