import unittest

from tools.gate_btc_factory.h1_recovery_policy import decide


class H1RecoveryPolicyTests(unittest.TestCase):
    def test_scheduled_failure_gets_one_explicit_date_retry(self):
        d = decide("schedule", 1, "2026-08-26")
        self.assertEqual(d.action, "DISPATCH_EXPLICIT_DATE_RETRY_ONCE")
        self.assertTrue(d.retry_allowed)
        self.assertFalse(d.production_blocking)

    def test_recovery_failure_does_not_loop(self):
        d = decide("workflow_dispatch", 1, "2026-08-26")
        self.assertEqual(d.action, "INCIDENT_CONFIRMED_AFTER_BOUNDED_RETRY")
        self.assertFalse(d.retry_allowed)

    def test_missing_target_date_fails_closed(self):
        d = decide("schedule", 1, "")
        self.assertEqual(d.action, "INCIDENT_FAIL_CLOSED")
        self.assertFalse(d.retry_allowed)

    def test_second_attempt_never_retries(self):
        d = decide("schedule", 2, "2026-08-26")
        self.assertEqual(d.action, "INCIDENT_CONFIRMED_AFTER_BOUNDED_RETRY")
        self.assertFalse(d.retry_allowed)

    def test_immutable_boundary(self):
        for event, attempt in [("schedule", 1), ("workflow_dispatch", 1), ("schedule", 2)]:
            d = decide(event, attempt, "2026-08-26")
            self.assertFalse(d.scientific_change_allowed)
            self.assertFalse(d.backfill_allowed)
            self.assertEqual(d.orders, 0)
            self.assertEqual(d.real_capital, 0)
            self.assertFalse(d.engine_feed)
            self.assertFalse(d.production_blocking)


if __name__ == "__main__":
    unittest.main()
