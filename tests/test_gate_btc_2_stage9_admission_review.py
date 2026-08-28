from __future__ import annotations

import copy
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.gate_btc_2_microstructure_shadow_contract import load_json
from tools.gate_btc_2_microstructure_shadow_manifest import DEFAULT_CONTRACT, SPECS, build_manifest
from tools.gate_btc_2_prospective_counter_bridge import build_counter, validate_admission
from tools.gate_btc_2_stage9_admission_review import validate_bundle


def ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_bundle(root: Path, run_id: int = 9001) -> Path:
    contract = load_json(DEFAULT_CONTRACT)
    created = datetime(2026, 8, 28, 12, 0, 10, tzinfo=timezone.utc)
    captured = created - timedelta(seconds=5)
    provider = captured - timedelta(seconds=5)
    opened = provider - timedelta(minutes=1)
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    payloads = {
        "FUNDING": {
            "symbol": "BTCUSDT",
            "lastFundingRate": "0.0001",
            "nextFundingTime": ms(created + timedelta(hours=8)),
            "time": ms(provider),
        },
        "OPEN_INTEREST": {
            "symbol": "BTCUSDT",
            "openInterest": "12345.67",
            "time": ms(provider),
        },
        "PERP_VOLUME": {
            "symbol": "BTCUSDT",
            "volume": "1000.0",
            "quoteVolume": "65000000.0",
            "openTime": ms(opened),
            "closeTime": ms(provider),
            "count": 100,
        },
        "SPOT_VOLUME": {
            "symbol": "BTCUSDT",
            "volume": "900.0",
            "quoteVolume": "58500000.0",
            "openTime": ms(opened),
            "closeTime": ms(provider),
            "count": 90,
        },
    }

    sources = []
    for role in contract["required_source_roles"]:
        spec = SPECS[role]
        write_json(raw_dir / spec["raw_file"], payloads[role])
        sources.append({
            "source_role": role,
            "raw_file": spec["raw_file"],
            "request_url": spec["url"],
            "captured_at_utc": captured.isoformat().replace("+00:00", "Z"),
        })

    receipt = {
        "schema": "gate_btc.2_0.microstructure_shadow_capture_receipt.v1",
        "capture_id": f"gate2-stage9-run-{run_id}",
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
        "contract_sha256": contract["contract_sha256"],
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "recovered_historical": False,
        "network_capture_job_count": 1,
        "sources": sources,
    }
    manifest = build_manifest(receipt, raw_dir, contract)
    decision = {
        "schema": "gate_btc.2_0.microstructure_shadow_capture_decision.v1",
        "checked_at_utc": created.isoformat().replace("+00:00", "Z"),
        "repository": "vmasardinha-coder/QRDS",
        "current_run_id": run_id,
        "active_or_queued_runs": [],
        "protected_active_workflows": [],
        "scheduled_active_or_queued_runs": [],
        "other_manual_capture_runs": [],
        "active_workflows_checked": True,
        "market_network_requests": 4,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "status": "CAPTURED_READY_FOR_FORWARD_CAPTURE_REVIEW",
        "capture_id": receipt["capture_id"],
        "required_source_roles_captured": list(contract["required_source_roles"]),
        "shadow_feeds_reconciled": False,
    }
    write_json(root / "capture_receipt.json", receipt)
    write_json(root / "capture_manifest.json", manifest)
    write_json(root / "capture_decision.json", decision)
    return root


class Stage9AdmissionReviewTests(unittest.TestCase):
    def test_valid_physical_bundle_emits_counter_eligible_admission(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td))
            review, admission = validate_bundle(capture)
            self.assertEqual(review["decision"], "ADMITTED_FORWARD_ONLY")
            self.assertTrue(review["physical_raw_hashes_verified"])
            self.assertTrue(review["canonical_manifest_replay_equal"])
            self.assertFalse(review["stage_9_complete"])
            validate_admission(admission)
            counter = build_counter([admission])
            self.assertEqual(counter["canonical_counter"], 1)
            self.assertEqual(counter["prospective_credit_from_backfill"], 0)

    def test_tampered_physical_bytes_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td))
            path = capture / "raw" / SPECS["OPEN_INTEREST"]["raw_file"]
            payload = json.loads(path.read_text())
            payload["openInterest"] = "99999.99"
            write_json(path, payload)
            with self.assertRaises((RuntimeError, ValueError)):
                validate_bundle(capture)

    def test_manifest_not_equal_to_canonical_replay_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td))
            manifest_path = capture / "capture_manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["sources"][0]["provider"] = "UNAUTHORIZED_ALIAS"
            write_json(manifest_path, manifest)
            with self.assertRaises(RuntimeError):
                validate_bundle(capture)

    def test_deferred_capture_cannot_be_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td))
            decision_path = capture / "capture_decision.json"
            decision = json.loads(decision_path.read_text())
            decision["status"] = "DEFER_NETWORK_CAPTURE_ACTIVE_SCHEDULE_OR_PROTECTED_WORKFLOW"
            decision["market_network_requests"] = 0
            write_json(decision_path, decision)
            with self.assertRaises(RuntimeError):
                validate_bundle(capture)

    def test_run_identity_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td), run_id=9002)
            decision_path = capture / "capture_decision.json"
            decision = json.loads(decision_path.read_text())
            decision["capture_id"] = "gate2-stage9-run-9999"
            write_json(decision_path, decision)
            with self.assertRaises(RuntimeError):
                validate_bundle(capture)

    def test_backfilled_receipt_is_rejected_by_canonical_builder(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td))
            receipt_path = capture / "capture_receipt.json"
            receipt = json.loads(receipt_path.read_text())
            receipt["historical_rows_backfilled"] = 1
            write_json(receipt_path, receipt)
            with self.assertRaises((RuntimeError, ValueError)):
                validate_bundle(capture)

    def test_admission_is_self_hash_bound(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_bundle(Path(td))
            _, admission = validate_bundle(capture)
            tampered = copy.deepcopy(admission)
            tampered["captured_at_utc"] = "2026-08-28T12:01:00Z"
            with self.assertRaises(RuntimeError):
                validate_admission(tampered)


if __name__ == "__main__":
    unittest.main()
