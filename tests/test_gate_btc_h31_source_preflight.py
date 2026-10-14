import unittest, tempfile, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from gate_btc_h31_source_preflight import source_preflight

class H31PreflightTests(unittest.TestCase):
    def test_current_session_reports_expired_calendar_without_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"STATUS.json";p.write_text("immutable")
            r=source_preflight("2026-10-13",{"2026-09-04":{}},d)
            self.assertFalse(r["target_session_bound"])
            self.assertEqual(r["operational_status"],"BLOCKED_TARGET_OUTSIDE_FROZEN_SOURCE_CALENDAR")
            self.assertEqual(r["last_frozen_source_session"],"2026-09-04")
            self.assertEqual(p.read_text(),"immutable")
            self.assertEqual(r["eligible_observation_increment"],0)

    def test_cache_is_not_observation_credit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"warmup";p.mkdir();(p/"2026-08-10.json").write_text("{}")
            r=source_preflight("2026-08-12",{"2026-08-10":{},"2026-08-11":{},"2026-08-12":{}},d)
            self.assertTrue(r["target_session_bound"])
            self.assertEqual(r["warmup_cache_missing_dates"],["2026-08-11"])
            self.assertEqual(r["eligible_observation_increment"],0)

    def test_empty_calendar_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(source_preflight("2026-10-13",{},d)["target_session_bound"])
