import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime as RealDatetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gate_btc_h1_schedule_extension as extension
import gate_btc_b3_h1_daily as collector
import gate_btc_b3_h1_runtime_ledger as publisher


class H1ScheduleExtensionTests(unittest.TestCase):
    def source(self, day="2026-10-23"):
        d = extension.load_extension()
        return {"schema": "gate_btc.b3.h1.cloud_structural.v2", "date": day,
                "status": "STRUCTURAL_PASS", "qualified": True, "h1_increment_candidate": 1,
                "research_only": True, "shadow_only": True, "not_approved": True,
                "orders": 0, "real_capital": 0, "economics_locked": True,
                "economic_functions_called": False,
                "front_contracts": {"WIN": "WINZ26", "WDO": "WDOX26"},
                "freeze_status": d["freeze_status"],
                "schedule_amendment_sha256": extension.EXTENSION_SHA256,
                "full_frozen_schedule_sha256": extension.FULL_SHA256,
                "h1_schedule_prefix_sha256": extension.PREFIX_SHA256,
                "qa": {"m1_to_m5_exact": True, "tick_grid": "PASS", "ohlc_integrity": "PASS"}}

    def mutated(self, change, error):
        d = copy.deepcopy(extension.load_extension())
        change(d)
        raw = json.dumps(d).encode()
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "extension.json"
            p.write_bytes(raw)
            with patch.object(extension, "EXTENSION_FILE", p), patch.object(extension, "EXTENSION_SHA256", hashlib.sha256(raw).hexdigest()):
                with self.assertRaisesRegex(RuntimeError, error):
                    extension.load_extension()

    def test_additive_future_dates_preserve_legacy(self):
        self.assertEqual(len(collector.load_schedule()), 20)
        self.assertEqual(len(collector.load_amendment_schedule()), 8)
        dates = extension.extension_schedule()
        self.assertEqual(list(dates), ["2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29"])
        self.assertFalse(set(dates) & set(collector.load_amendment_schedule()))
        self.assertNotIn("2026-10-21", dates)
        self.assertNotIn("2026-10-22", dates)

    def test_original_contract_bytes_unchanged(self):
        self.assertEqual(hashlib.sha256(collector.AMENDMENT_FILE.read_bytes()).hexdigest(), collector.AMENDMENT_SHA256)

    def test_valid_new_artifact_and_idempotent_publication(self):
        good = self.source()
        publisher.validate_source(good)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "status.json"
            p.write_text(json.dumps(good))
            original = {"entries": [{"date": "2026-10-20", "qualified": True, "evidence": "preserved"}]}
            before = copy.deepcopy(original)
            result = publisher.build(good, p, original, "test")
            self.assertEqual(original, before)
            self.assertEqual(result["entries"][0], before["entries"][0])
            again = publisher.build(good, p, result, "test2")
            self.assertEqual(again["entries"], result["entries"])

    def test_wrong_contract_or_amendment_cannot_publish(self):
        for field, value in [("front_contracts", {"WIN": "WINV26", "WDO": "WDOX26"}),
                             ("schedule_amendment_sha256", collector.AMENDMENT_SHA256),
                             ("date", "2026-10-22")]:
            d = self.source(); d[field] = value
            with self.assertRaises(RuntimeError):
                publisher.validate_source(d)

    def test_rejects_tampered_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "extension.json"
            p.write_bytes(extension.EXTENSION_FILE.read_bytes() + b" ")
            with patch.object(extension, "EXTENSION_FILE", p):
                with self.assertRaisesRegex(RuntimeError, "HASH_MISMATCH"):
                    extension.load_extension()

    def test_rejects_late_or_naive_registration(self):
        for value in ["2026-10-23T12:00:00Z", "2026-10-23T13:00:00Z", "2026-10-22T12:00:00"]:
            self.mutated(lambda d: d.update(preregistered_at_utc=value), "NOT_FROZEN")

    def test_rejects_duplicated_or_historical_session(self):
        self.mutated(lambda d: d["sessions"][1].update(date="2026-10-23"), "SESSION_LIST")
        self.mutated(lambda d: d["sessions"][0].update(date="2026-10-22"), "SESSION_LIST")

    def test_rejects_changed_parent_safety_or_qa(self):
        self.mutated(lambda d: d.update(parent_amendment_sha256="0" * 64), "LEGACY_SEALS")
        self.mutated(lambda d: d["safety"].update(economics_locked=False), "SAFETY")
        self.mutated(lambda d: d["qa_unchanged"].update(expected_m5_per_root=101), "QA_CHANGED")

    def test_collector_refuses_future_and_expired_dates_without_fetch(self):
        class Clock(RealDatetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 22, 13, tzinfo=tz)
        for today in [Clock, type("LateClock", (Clock,), {"now": classmethod(lambda cls, tz=None: cls(2026, 10, 26, 13, tzinfo=tz))})]:
            with tempfile.TemporaryDirectory() as tmp, patch.object(collector, "datetime", today), patch.object(collector, "fetch_raw") as fetch:
                with patch.object(sys, "argv", ["collector", "--date", "2026-10-23", "--out-dir", tmp]):
                    self.assertEqual(collector.main(), 0)
                s = json.loads((Path(tmp) / "2026-10-23/H1_STRUCTURAL_STATUS.json").read_text())
                self.assertEqual(s["status"], "PROSPECTIVE_WINDOW_EXPIRED_OR_NOT_OPEN")
                self.assertEqual(s["h1_increment_candidate"], 0)
                fetch.assert_not_called()

    def test_existing_canonical_gate_stops_at_twenty(self):
        path = ROOT / "tools/gate_btc_factory/h1_canonical_runtime.py"
        spec = importlib.util.spec_from_file_location("canonical", path)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        anchor = {"canonical_evidence": {"qualified": 8, "last_candidate_date": "2026-08-28"}}
        before = {"qualified": 17, "post_anchor_events": []}
        for day in ["2026-10-23", "2026-10-26", "2026-10-27"]:
            before = module.build(anchor, before, day, "qualified", "STRUCTURAL_PASS", "test")
        self.assertEqual(before["qualified"], 20)
        self.assertTrue(before["economics_locked"])
        self.assertFalse(before["collector_should_continue"])
        with self.assertRaisesRegex(RuntimeError, "already at 20"):
            module.build(anchor, before, "2026-10-28", "qualified", "STRUCTURAL_PASS", "test")

    def test_new_session_records_extension_seal_even_when_source_pending(self):
        class Clock(RealDatetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 10, 23, 22, tzinfo=tz)
        with tempfile.TemporaryDirectory() as tmp, patch.object(collector, "datetime", Clock), patch.object(collector, "fetch_raw", return_value=(None, {"state": "PENDING_SOURCE_NOT_PUBLISHED"})):
            with patch.object(sys, "argv", ["collector", "--date", "2026-10-23", "--out-dir", tmp]):
                self.assertEqual(collector.main(), 0)
            s = json.loads((Path(tmp) / "2026-10-23/H1_STRUCTURAL_STATUS.json").read_text())
            self.assertEqual(s["schedule_amendment_sha256"], extension.EXTENSION_SHA256)
            self.assertEqual(s["freeze_status"], extension.load_extension()["freeze_status"])
            self.assertEqual(s["h1_increment_candidate"], 0)

    def test_clock_uses_same_v2_runner_as_exit_guard_with_preflight(self):
        clock = (ROOT / "tools/gate_btc_local_shadow_clock.ps1").read_text()
        self.assertIn("$h1=Join-Path $Root 'local_h1_opening_v2\\run_h1.py'", clock)
        self.assertNotIn("$h1='tools\\gate_btc_h1_inspired_challenger_entrypoint.py'", clock)
        self.assertIn("$bindingProbe = & $Py $h1 --deployment-check", clock)
        self.assertLess(clock.index("H1_V2_BINDING_NOT_VERIFIED"), clock.index("while((Get-Date) -lt $start)"))


if __name__ == "__main__":
    unittest.main()
