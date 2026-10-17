import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from gate_btc_win_session_phase_qa import session_phase_qa

class SessionPhaseTests(unittest.TestCase):
    def rows(self, session="2026-10-15", count=113):
        t = datetime.fromisoformat(session + "T09:00:00-03:00")
        rows = [{"timestamp": (t+timedelta(minutes=5*i)).isoformat(), "close": i+1} for i in range(count)]
        rows.append({"timestamp":session+"T18:30:00-03:00", "close":999})
        return rows

    def test_regular_grid_and_call_gap_preserve_prices(self):
        rows = self.rows()
        before = repr(rows)
        r = session_phase_qa(rows,"2026-10-15","2026-12-16",60)
        self.assertTrue(r["pass"])
        self.assertEqual(r["expected_regular_bars"],113)
        self.assertEqual(r["observed_call_or_post_regular_bars"],1)
        self.assertEqual(repr(rows),before)

    def test_missing_regular_bar_still_fails(self):
        rows=self.rows();del rows[30]
        self.assertFalse(session_phase_qa(rows,"2026-10-15","2026-12-16",60)["pass"])

    def test_old_session_is_not_requalified(self):
        self.assertFalse(session_phase_qa(self.rows("2026-10-13"),"2026-10-13","2026-10-14",60)["pass"])

    def test_expiry_has_96_regular_bars(self):
        rows=self.rows(count=96)
        self.assertTrue(session_phase_qa(rows,"2026-10-15","2026-10-15",60)["pass"])
        self.assertFalse(session_phase_qa(self.rows(),"2026-10-15","2026-10-15",60)["pass"])

    def test_duplicate_and_wrong_day_fail(self):
        rows=self.rows();rows.insert(1,dict(rows[0]))
        self.assertFalse(session_phase_qa(rows,"2026-10-15","2026-12-16",60)["pass"])
        rows=self.rows();rows[-1]["timestamp"]="2026-10-16T18:30:00-03:00"
        self.assertFalse(session_phase_qa(rows,"2026-10-15","2026-12-16",60)["pass"])


    def test_two_post_regular_bars_do_not_reject_future_complete_regular_grid(self):
        rows = self.rows('2026-10-19')
        rows.insert(-1, {'timestamp': '2026-10-19T18:25:00-03:00', 'close': 777})
        before = repr(rows)
        result = session_phase_qa(rows, '2026-10-19', '2026-12-16', 90)
        self.assertTrue(result['pass'])
        self.assertEqual(result['observed_regular_bars'], 113)
        self.assertEqual(result['observed_call_or_post_regular_bars'], 2)
        self.assertTrue(result['post_regular_count_independent'])
        self.assertEqual(repr(rows), before)

    def test_old_two_post_regular_bar_decision_is_preserved(self):
        rows = self.rows('2026-10-16')
        rows.insert(-1, {'timestamp': '2026-10-16T18:25:00-03:00', 'close': 777})
        self.assertFalse(session_phase_qa(rows, '2026-10-16', '2026-12-16', 90)['pass'])

    def test_post_regular_bars_cannot_replace_a_missing_regular_bar(self):
        rows = self.rows('2026-10-19')
        rows.insert(-1, {'timestamp': '2026-10-19T18:25:00-03:00', 'close': 777})
        del rows[30]
        self.assertFalse(session_phase_qa(rows, '2026-10-19', '2026-12-16', 90)['pass'])

    def test_future_tail_still_rejects_duplicate_wrong_grid_and_after_hours(self):
        for timestamp in ['2026-10-19T18:30:00-03:00', '2026-10-19T18:31:00-03:00',
                          '2026-10-19T19:00:00-03:00', '2026-10-20T18:35:00-03:00']:
            with self.subTest(timestamp=timestamp):
                rows = self.rows('2026-10-19')
                rows.append({'timestamp': timestamp, 'close': 777})
                self.assertFalse(session_phase_qa(rows, '2026-10-19', '2026-12-16', 90)['pass'])


    def test_call_prices_do_not_change_frozen_intraday_features(self):
        from gate_btc_2_item3c_forward_collector import raw_feature
        rows = self.rows('2026-10-19')[:-1]
        for i, row in enumerate(rows):
            row.update(open=100+i, close=101+i, high=103+i, low=99+i, real_volume=10+i)
        extended = rows + [dict(timestamp='2026-10-19T18:25:00-03:00', open=1, close=999999,
                                high=999999, low=1, real_volume=999999),
                           dict(timestamp='2026-10-19T18:30:00-03:00', open=999999, close=1,
                                high=999999, low=1, real_volume=999999)]
        for feature in ('OPEN_RETURN', 'OPEN_RANGE', 'REALIZED_VOL', 'VOLUME_EARLY',
                        'BAR_IMBALANCE', 'CLOSE_LOCATION', 'BODY_RANGE', 'GAP_FROM_PRIOR_CLOSE'):
            for window in (15, 30, 60, 90):
                with self.subTest(feature=feature, window=window):
                    self.assertEqual(raw_feature(feature, rows, window, 100),
                                     raw_feature(feature, extended, window, 100))
