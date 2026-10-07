import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gate_btc_b3_h1_daily as collector
from tools import gate_btc_b3_h1_runtime_ledger as publisher


class H1ProspectiveAmendmentTests(unittest.TestCase):
    def source(self, date="2026-10-08"):
        prospective = collector.load_amendment_schedule()
        return {
            "schema": "gate_btc.b3.h1.cloud_structural.v2",
            "date": date,
            "status": "STRUCTURAL_PASS", "qualified": True,
            "h1_increment_candidate": 1,
            "research_only": True, "shadow_only": True, "not_approved": True,
            "orders": 0, "real_capital": 0, "economics_locked": True,
            "economic_functions_called": False,
            "front_contracts": prospective[date],
            "freeze_status": "FROZEN_BEFORE_SESSION_AMENDMENT_V1",
            "schedule_amendment_sha256": collector.AMENDMENT_SHA256,
            "full_frozen_schedule_sha256": collector.FULL_FROZEN_SCHEDULE_SHA256,
            "h1_schedule_prefix_sha256": collector.H1_PREFIX_SHA256,
            "qa": {"m1_to_m5_exact": True, "tick_grid": "PASS",
                   "ohlc_integrity": "PASS"},
        }

    def test_legacy_schedule_unchanged_and_new_dates_predeclared(self):
        legacy = collector.load_schedule()
        future = collector.load_amendment_schedule()
        self.assertEqual(len(legacy), 20)
        self.assertEqual(legacy["2026-09-04"], {"WIN": "WINV26", "WDO": "WDOV26"})
        self.assertEqual(len(future), 8)
        self.assertEqual(future["2026-10-08"], {"WIN": "WINV26", "WDO": "WDOX26"})
        self.assertEqual(future["2026-10-15"], {"WIN": "WINZ26", "WDO": "WDOX26"})
        self.assertNotIn("2026-10-12", future)

    def test_new_structural_pass_requires_exact_amendment_and_fronts(self):
        good = self.source()
        publisher.validate_source(good)
        missing = dict(good); missing.pop("schedule_amendment_sha256")
        with self.assertRaisesRegex(RuntimeError, "AMENDMENT_EVIDENCE_MISSING"):
            publisher.validate_source(missing)
        wrong = dict(good); wrong["front_contracts"] = {"WIN": "WINZ26", "WDO": "WDOX26"}
        with self.assertRaisesRegex(RuntimeError, "UNDECLARED"):
            publisher.validate_source(wrong)
        wrong_day = dict(good); wrong_day["date"] = "2026-10-07"
        with self.assertRaisesRegex(RuntimeError, "UNDECLARED"):
            publisher.validate_source(wrong_day)

    def test_contract_bytes_are_pinned_and_old_freeze_still_valid(self):
        raw = collector.AMENDMENT_FILE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            altered = Path(tmp) / "amendment.json"
            altered.write_bytes(raw + b" ")
            with patch.object(collector, "AMENDMENT_FILE", altered):
                with self.assertRaisesRegex(RuntimeError, "HASH_MISMATCH"):
                    collector.load_amendment_schedule()
        old = self.source()
        old.update(date="2026-09-04", front_contracts={"WIN": "WINV26", "WDO": "WDOV26"},
                   freeze_status="FROZEN_BEFORE_H1")
        old.pop("schedule_amendment_sha256")
        publisher.validate_source(old)


if __name__ == "__main__":
    unittest.main()
