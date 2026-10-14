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
