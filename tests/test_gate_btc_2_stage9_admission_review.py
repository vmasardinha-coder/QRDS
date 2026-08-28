from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_2_microstructure_shadow_contract import load_json
from tools.gate_btc_2_microstructure_shadow_capture import DECISION_SCHEMA
from tools.gate_btc_2_microstructure_shadow_manifest import DEFAULT_CONTRACT, RECEIPT_SCHEMA, SPECS, build_manifest
from tools.gate_btc_2_prospective_counter_bridge import build_counter
from tools.gate_btc_2_stage9_admission_review import REVIEW_SCHEMA, review_capture


def ms(ts: str) -> int:
    return int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)


def dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_capture(root: Path, run_id: int = 9001) -> Path:
    contract = load_json(DEFAULT_CONTRACT)
    capture = root / "capture"
    raw = capture / "raw"
    raw.mkdir(parents=True)

    provider_time = "2026-08-28T12:00:00Z"
    payloads = {
        "FUNDING": {
            "symbol": "BTCUSDT",
            "lastFundingRate": "0.00010000",
            "nextFundingTime": ms("2026-08-28T16:00:00Z"),
            "time": ms(provider_time),
        },
        "OPEN_INTEREST": {
            "symbol": "BTCUSDT",
            "openInterest": "12345.67",
            "time": ms(provider_time),
        },
        "PERP_VOLUME": {
            "symbol": "BTCUSDT",
            "volume": "100.0",
            "quoteVolume": "6000000.0",
            "openTime": ms("2026-08-28T11:00:00Z"),
            "closeTime": ms(provider_time),
            "count": 100,
        },
        "SPOT_VOLUME": {
            "symbol": "BTCUSDT",
            "volume": "80.0",
            "quoteVolume": "4800000.0",
            "openTime": ms("2026-08-28T11:00:00Z"),
            "closeTime": ms(provider_time),
            "count": 80,
        },
    }
    captured_times = {
        "FUNDING": "2026-08-28T12:00:05Z",
        "OPEN_INTEREST": "2026-08-28T12:00:06Z",
        "PERP_VOLUME": "2026-08-28T12:00:07Z",
        "SPOT_VOLUME": "2026-08-28T12:00:08Z",
    }
    sources = []
    for role in contract["required_source_roles"]:
        spec = SPECS[role]
        dump(raw / spec["raw_file"], payloads[role])
        sources.append({
            "source_role": role,
            "raw_file": spec["raw_file"],
            "request_url": spec["url"],
            "captured_at_utc": captured_times[role],
        })

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "capture_id": f"gate2-stage9-run-{run_id}",
        "created_at_utc": "2026-08-28T12:00:10Z",
        "contract_sha256": contract["contract_sha256"],
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "recovered_historical": False,
        "network_capture_job_count": 1,
        "sources": sources,
    }
    dump(capture / "capture_receipt.json", receipt)
    manifest = build_manifest(receipt, raw, contract)
    dump(capture / "capture_manifest.json", manifest)

    decision = {
        "schema": DECISION_SCHEMA,
        "checked_at_utc": "2026-08-28T11:59:59Z",
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
        "required_source_roles_captured": contract["required_source_roles"],
        "shadow_feeds_reconciled": False,
    }
    dump(capture / "capture_decision.json", decision)
    return capture


class Stage9AdmissionReviewTests(unittest.TestCase):
    def test_valid_physical_capture_emits_one_non_promoting_admission(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_capture(Path(td))
            review, admission = review_capture(capture)
            self.assertEqual(review["schema"], REVIEW_SCHEMA)
            self.assertEqual(review["status"], "ADMITTED_FORWARD_ONLY_CAPTURE")
            self.assertEqual(review["prospective_observations_admitted"], 1)
            self.assertFalse(review["stage_9_complete"])
            self.assertFalse(review["economics_allowed"])
            self.assertFalse(review["engine_feed"])
            self.assertEqual(review["orders_generated"], 0)
            self.assertEqual(review["real_capital_used"], 0)
            self.assertEqual(admission["decision"], "ADMITTED_FORWARD_ONLY")
            counter = build_counter([admission])
            self.assertEqual(counter["canonical_counter"], 1)
            self.assertEqual(counter["prospective_credit_from_backfill"], 0)

    def test_tampered_raw_bytes_fail_review(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_capture(Path(td))
            path = capture / "raw" / SPECS["OPEN_INTEREST"]["raw_file"]
            payload = json.loads(path.read_text())
            payload["openInterest"] = "99999"
            dump(path, payload)
            with self.assertRaises((RuntimeError, ValueError)):
                review_capture(capture)

    def test_tampered_manifest_fails_deterministic_rebuild(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_capture(Path(td))
            path = capture / "capture_manifest.json"
            payload = json.loads(path.read_text())
            payload["sources"][0]["content_sha256"] = "0" * 64
            dump(path, payload)
            with self.assertRaises((RuntimeError, ValueError)):
                review_capture(capture)

    def test_deferred_or_unsafe_decision_cannot_admit(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_capture(Path(td))
            path = capture / "capture_decision.json"
            payload = json.loads(path.read_text())
            payload["status"] = "DEFER_NETWORK_CAPTURE_ACTIVE_SCHEDULE_OR_PROTECTED_WORKFLOW"
            payload["market_network_requests"] = 0
            dump(path, payload)
            with self.assertRaises(RuntimeError):
                review_capture(capture)

    def test_stage9_complete_or_economics_flag_cannot_sneak_through(self):
        for key in ("stage_9_complete", "economics_allowed", "engine_feed", "promotion_allowed"):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as td:
                capture = make_capture(Path(td))
                path = capture / "capture_decision.json"
                payload = json.loads(path.read_text())
                payload[key] = True
                dump(path, payload)
                with self.assertRaises(RuntimeError):
                    review_capture(capture)

    def test_wrong_run_binding_cannot_admit(self):
        with tempfile.TemporaryDirectory() as td:
            capture = make_capture(Path(td), run_id=9001)
            path = capture / "capture_decision.json"
            payload = json.loads(path.read_text())
            payload["current_run_id"] = 9002
            dump(path, payload)
            with self.assertRaises(RuntimeError):
                review_capture(capture)


if __name__ == "__main__":
    unittest.main()
