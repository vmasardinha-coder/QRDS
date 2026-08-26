import copy
import json
import unittest
from pathlib import Path

from tools.gate_btc_2_microstructure_shadow_contract import (
    assess,
    canonical_hash,
    validate_contract,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "tools" / "gate_btc_2_microstructure_shadow_contract_v1.json"


def source(role: str, index: int) -> dict:
    return {
        "source_id": f"source-{index}",
        "source_role": role,
        "provider": "fixture-provider",
        "venue": "fixture-venue",
        "market_type": "linear_perpetual" if role != "SPOT_VOLUME" else "spot",
        "instrument": "BTC-USDT",
        "source_reference": f"fixture://{role.lower()}",
        "captured_at_utc": "2026-08-26T08:00:00Z",
        "first_observation_utc": "2026-08-26T07:00:00Z",
        "last_observation_utc": "2026-08-26T07:59:00Z",
        "row_count": 60,
        "content_sha256": f"{index + 1:064x}",
    }


def manifest() -> dict:
    roles = ["FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME"]
    return {
        "schema": "gate_btc.2_0.microstructure_shadow_capture_manifest.v1",
        "capture_id": "fixture-20260826T080000Z",
        "created_at_utc": "2026-08-26T08:00:00Z",
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "recovered_historical": False,
        "sources": [source(role, index) for index, role in enumerate(roles)],
    }


class MicrostructureShadowContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_is_hash_bound_and_fail_closed(self):
        self.assertEqual(self.contract["contract_sha256"], canonical_hash(self.contract))
        self.assertEqual(validate_contract(self.contract), [])
        self.assertEqual(self.contract["stage_id"], 9)
        self.assertFalse(self.contract["safety"]["stage_9_complete"])
        self.assertFalse(self.contract["safety"]["economic_calibration_allowed"])

    def test_scaffold_does_not_claim_capture_or_reconciliation(self):
        payload = assess(self.contract)
        self.assertEqual(payload["status"], "SCAFFOLD_READY_CAPTURE_NOT_STARTED")
        self.assertTrue(payload["network_capture_allowed_now"])
        self.assertFalse(payload["shadow_feeds_reconciled"])
        self.assertFalse(payload["stage_9_complete"])
        self.assertFalse(payload["economics_allowed"])

    def test_protected_active_workflow_defers_network_capture(self):
        payload = assess(
            self.contract,
            active_workflows=["GATE BTC Daily Research Collection"],
        )
        self.assertEqual(payload["status"], "DEFER_NETWORK_CAPTURE_ACTIVE_PROTECTED_WORKFLOW")
        self.assertFalse(payload["network_capture_allowed_now"])
        self.assertEqual(
            payload["protected_active_workflows"],
            ["GATE BTC Daily Research Collection"],
        )

    def test_all_required_roles_are_needed(self):
        candidate = manifest()
        candidate["sources"] = candidate["sources"][:-1]
        payload = assess(self.contract, candidate)
        self.assertEqual(payload["status"], "BLOCKED_CAPTURE_MANIFEST")
        self.assertIn("REQUIRED_ROLE_MISSING_SPOT_VOLUME", payload["manifest_errors"])

    def test_recovered_or_backfilled_history_is_never_forward_capture(self):
        candidate = manifest()
        candidate["recovered_historical"] = True
        candidate["historical_rows_backfilled"] = 1
        payload = assess(self.contract, candidate)
        self.assertEqual(payload["status"], "BLOCKED_CAPTURE_MANIFEST")
        self.assertIn("HISTORICAL_BACKFILL_PRESENT", payload["manifest_errors"])
        self.assertIn(
            "RECOVERED_HISTORY_CANNOT_ENTER_FORWARD_CAPTURE",
            payload["manifest_errors"],
        )

    def test_complete_manifest_only_reaches_explicit_review(self):
        payload = assess(self.contract, manifest())
        self.assertEqual(payload["status"], "READY_FOR_FORWARD_CAPTURE_REVIEW")
        self.assertEqual(payload["manifest_errors"], [])
        self.assertFalse(payload["shadow_feeds_reconciled"])
        self.assertFalse(payload["stage_9_complete"])
        self.assertFalse(payload["economics_allowed"])
        self.assertEqual(payload["orders_generated"], 0)
        self.assertEqual(payload["real_capital_used"], 0)

    def test_contract_safety_mutation_blocks_preflight(self):
        unsafe = copy.deepcopy(self.contract)
        unsafe["safety"]["engine_feed"] = True
        unsafe["contract_sha256"] = canonical_hash(unsafe)
        payload = assess(unsafe)
        self.assertEqual(payload["status"], "BLOCKED_INVALID_CONTRACT")
        self.assertIn("SAFETY_BOUNDARY_INVALID", payload["contract_errors"])


if __name__ == "__main__":
    unittest.main()
