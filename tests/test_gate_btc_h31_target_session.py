import unittest
from datetime import datetime, timezone, timedelta
from tools.gate_btc_h31_target_session import resolve_target


class TargetSessionTests(unittest.TestCase):
    def test_sunday_push_keeps_saturday_and_skips(self):
        out = resolve_target(datetime(2026, 10, 18, 15, tzinfo=timezone.utc))
        self.assertEqual(out, {"date": "2026-10-17", "eligible": False,
                              "status": "NOOP_NON_B3_WEEKDAY_TARGET"})

    def test_monday_keeps_sunday_without_rolling_back_to_friday(self):
        out = resolve_target(datetime(2026, 10, 19, 1, tzinfo=timezone.utc))
        self.assertEqual(out["date"], "2026-10-18")
        self.assertFalse(out["eligible"])

    def test_normal_saturday_collection_still_targets_friday(self):
        out = resolve_target(datetime(2026, 10, 17, 1, tzinfo=timezone.utc))
        self.assertEqual(out["date"], "2026-10-16")
        self.assertTrue(out["eligible"])

    def test_next_scheduled_tuesday_targets_monday(self):
        out = resolve_target(datetime(2026, 10, 20, 0, 45, tzinfo=timezone.utc))
        self.assertEqual(out["date"], "2026-10-19")
        self.assertTrue(out["eligible"])

    def test_clock_is_utc_even_if_input_has_brt_offset(self):
        out = resolve_target(datetime(2026, 10, 19, 22, 0, tzinfo=timezone(timedelta(hours=-3))))
        self.assertEqual(out["date"], "2026-10-19")
        self.assertTrue(out["eligible"])

    def test_naive_clock_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_target(datetime(2026, 10, 18))
