import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from tools.gate_btc_2_microstructure_shadow_capture import run_capture
from tools.gate_btc_2_microstructure_shadow_manifest import SPECS


NOW = datetime(2026, 8, 26, 15, 0, tzinfo=timezone.utc)
NOW_MS = int(NOW.timestamp() * 1000)


def market_payload(url):
    if "premiumIndex" in url:
        return {"symbol": "BTCUSDT", "lastFundingRate": "-0.0001", "nextFundingTime": NOW_MS + 1000, "time": NOW_MS}
    if "openInterest" in url:
        return {"symbol": "BTCUSDT", "openInterest": "12345.67", "time": NOW_MS}
    base = {"symbol": "BTCUSDT", "volume": "100", "quoteVolume": "5000000", "openTime": NOW_MS - 86400000, "closeTime": NOW_MS, "count": 1000}
    return base


class FakeFetch:
    def __init__(self, runs=None):
        self.runs = runs or []
        self.urls = []

    def __call__(self, url, headers):
        self.urls.append(url)
        if "api.github.com" in url:
            status = "queued" if "status=queued" in url else "in_progress"
            rows = [row for row in self.runs if row["status"] == status]
            return json.dumps({"total_count": len(rows), "workflow_runs": rows}).encode()
        return (json.dumps(market_payload(url), separators=(",", ":")) + "\n").encode()


class SourceBlockedFetch(FakeFetch):
    def __call__(self, url, headers):
        if "api.github.com" in url:
            return super().__call__(url, headers)
        self.urls.append(url)
        raise urllib.error.HTTPError(url, 451, "Unavailable For Legal Reasons", {}, None)


class MicrostructureShadowCaptureTests(unittest.TestCase):
    def execute_capture(self, fetcher):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            decision = run_capture(root, "owner/repo", 900, fetcher=fetcher, now=lambda: NOW)
            files = {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}
            return decision, files

    def test_protected_workflow_defers_before_market_request(self):
        fetcher = FakeFetch([{"id": 1, "name": "GATE BTC Daily Research Collection", "event": "workflow_dispatch", "status": "in_progress"}])
        decision, files = self.execute_capture(fetcher)
        self.assertEqual(decision["status"], "DEFER_NETWORK_CAPTURE_ACTIVE_SCHEDULE_OR_PROTECTED_WORKFLOW")
        self.assertEqual(decision["market_network_requests"], 0)
        self.assertEqual(len(fetcher.urls), 2)
        self.assertEqual(set(files), {"capture_decision.json"})

    def test_any_scheduled_run_defers_before_market_request(self):
        fetcher = FakeFetch([{"id": 2, "name": "UNRELATED SCHEDULE", "event": "schedule", "status": "queued"}])
        decision, _ = self.execute_capture(fetcher)
        self.assertEqual(decision["status"], "DEFER_NETWORK_CAPTURE_ACTIVE_SCHEDULE_OR_PROTECTED_WORKFLOW")
        self.assertEqual(len(fetcher.urls), 2)

    def test_current_run_is_excluded_from_gate(self):
        fetcher = FakeFetch([{"id": 900, "name": "SELF", "event": "schedule", "status": "in_progress"}])
        decision, _ = self.execute_capture(fetcher)
        self.assertEqual(decision["status"], "CAPTURED_READY_FOR_FORWARD_CAPTURE_REVIEW")

    def test_second_manual_capture_run_defers(self):
        fetcher = FakeFetch([{"id": 901, "name": "GATE BTC 2 Microstructure Shadow Manual Capture", "event": "workflow_dispatch", "status": "queued"}])
        decision, _ = self.execute_capture(fetcher)
        self.assertEqual(decision["status"], "DEFER_NETWORK_CAPTURE_ACTIVE_SCHEDULE_OR_PROTECTED_WORKFLOW")
        self.assertEqual(decision["market_network_requests"], 0)

    def test_source_http_error_is_recorded_fail_closed(self):
        fetcher = SourceBlockedFetch()
        decision, files = self.execute_capture(fetcher)
        self.assertEqual(decision["status"], "BLOCKED_SOURCE")
        self.assertEqual(decision["failed_source_role"], "FUNDING")
        self.assertEqual(decision["market_network_requests"], 1)
        self.assertEqual(decision["required_source_roles_captured"], [])
        self.assertTrue(decision["partial_raw_discarded"])
        self.assertFalse(decision["stage_9_complete"])
        self.assertEqual(set(files), {"capture_decision.json"})

    def test_free_schedule_captures_exactly_four_frozen_sources(self):
        fetcher = FakeFetch()
        decision, files = self.execute_capture(fetcher)
        self.assertEqual(decision["status"], "CAPTURED_READY_FOR_FORWARD_CAPTURE_REVIEW")
        self.assertEqual(decision["market_network_requests"], 4)
        self.assertEqual(fetcher.urls[2:], [spec["url"] for spec in SPECS.values()])
        self.assertEqual(set(files), {
            "capture_decision.json", "capture_manifest.json", "capture_receipt.json",
            "raw/funding.json", "raw/open_interest.json", "raw/perp_volume.json", "raw/spot_volume.json",
        })
        manifest = json.loads(files["capture_manifest.json"])
        self.assertEqual(len(manifest["sources"]), 4)
        self.assertEqual(manifest["historical_rows_backfilled"], 0)
        self.assertFalse(manifest["recovered_historical"])

    def test_non_json_github_gate_fails_before_market_request(self):
        urls = []
        def fetcher(url, headers):
            urls.append(url)
            return b"not-json"
        with tempfile.TemporaryDirectory() as td, self.assertRaisesRegex(RuntimeError, "not valid JSON"):
            run_capture(Path(td), "owner/repo", 900, fetcher=fetcher, now=lambda: NOW)
        self.assertEqual(len(urls), 1)

    def test_safety_boundary_is_exact_in_success_and_defer(self):
        success, _ = self.execute_capture(FakeFetch())
        deferred, _ = self.execute_capture(FakeFetch([{"id": 3, "name": "OTHER", "event": "schedule", "status": "queued"}]))
        blocked, _ = self.execute_capture(SourceBlockedFetch())
        for row in (success, deferred, blocked):
            self.assertTrue(row["research_only"])
            self.assertTrue(row["shadow_only"])
            self.assertTrue(row["not_approved"])
            self.assertFalse(row["stage_9_complete"])
            self.assertFalse(row["economics_allowed"])
            self.assertFalse(row["engine_feed"])
            self.assertEqual(row["orders_generated"], 0)
            self.assertEqual(row["real_capital_used"], 0)

    def test_manual_workflow_has_no_automatic_trigger(self):
        workflow = Path(__file__).resolve().parents[1] / ".github/workflows/gate-btc-2-microstructure-shadow-manual-capture.yml"
        text = workflow.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("schedule:", text)
        self.assertNotIn("pull_request:", text)


if __name__ == "__main__":
    unittest.main()
