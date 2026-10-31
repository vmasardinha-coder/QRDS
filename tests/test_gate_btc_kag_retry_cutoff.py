import unittest
from tools.gate_btc_pit150_retry_policy import decision, load_policy


class KagRetryCutoffTests(unittest.TestCase):
    def test_kag_pause_does_not_rewrite_prior_cutoffs_or_other_identity(self):
        self.assertIsNone(decision('KAG', 'kinesis-silver', '2026-10-28'))
        self.assertIsNone(decision('KAG', 'different-token', '2026-10-29'))
        self.assertIsNone(decision('KAU', 'kinesis-silver', '2026-10-29'))

    def test_pause_stops_requests_but_preserves_coverage_gap(self):
        for day in ('2026-10-29', '2026-11-05', '2027-01-01'):
            result = decision('KAG', 'kinesis-silver', day)
            self.assertEqual(result['source_requests'], 0)
            self.assertTrue(result['requires_new_evidence'])
            self.assertIsNone(result['next_retry_cutoff'])
            self.assertFalse(result['coverage_repaired'])
            self.assertFalse(result['denominator_changed'])

    def test_existing_history_due_dates_and_core_remain_unchanged(self):
        self.assertEqual(load_policy()['legacy_denominator'], 150)
        self.assertEqual(decision('APXUSD', 'apxusd', '2026-10-29')['next_retry_cutoff'], '2026-11-05')
        self.assertIsNone(decision('APXUSD', 'apxusd', '2026-11-05'))
        self.assertIsNone(decision('BTC', 'bitcoin', '2026-10-29'))
        self.assertIsNone(decision('ETH', 'ethereum', '2026-10-29'))
        self.assertIsNone(decision('PEARL', 'pearl-2', '2026-10-29'))


if __name__ == '__main__':
    unittest.main()
