import unittest
from tools.gate_btc_b3_intraday_calendar_guard import evaluate

class CalendarGuardTests(unittest.TestCase):
    def test_official_holiday_skips_without_credit(self):
        r=evaluate('2026-10-12')
        self.assertEqual(r['decision'],'SKIP_KNOWN_NON_SESSION')
        self.assertEqual(r['reason'],'OFFICIAL_B3_CLOSED_2026')
        self.assertEqual(r['eligible_observation_increment'],0)
        self.assertEqual(r['scientific_credit'],0)
        self.assertEqual(r['orders'],0)
        self.assertFalse(r['engine_feed'])
    def test_following_session_still_requires_source_guards(self):
        r=evaluate('2026-10-13')
        self.assertEqual(r['decision'],'CONTINUE_EXISTING_SOURCE_GUARDS')
        self.assertTrue(r['does_not_assert_live_source_ready'])
    def test_sao_paulo_holiday_is_not_a_b3_closure(self):
        self.assertEqual(evaluate('2026-07-09')['decision'],'CONTINUE_EXISTING_SOURCE_GUARDS')
    def test_weekend_skips_without_fabricating_observation(self):
        r=evaluate('2026-10-11')
        self.assertEqual(r['decision'],'SKIP_KNOWN_NON_SESSION')
        self.assertEqual(r['reason'],'WEEKEND')
    def test_unknown_year_does_not_claim_open_or_extend_calendar(self):
        r=evaluate('2027-01-01')
        self.assertEqual(r['decision'],'CONTINUE_EXISTING_SOURCE_GUARDS')
        self.assertTrue(r['does_not_assert_live_source_ready'])
    def test_special_open_is_not_a_full_day_closure(self):
        self.assertEqual(evaluate('2026-02-18')['decision'],'CONTINUE_EXISTING_SOURCE_GUARDS')
    def test_invalid_date_fails_instead_of_allowing_collection(self):
        with self.assertRaises(ValueError):evaluate('not-a-date')

if __name__=='__main__':unittest.main()
