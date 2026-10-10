import sys
from datetime import datetime, timedelta
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from gate_btc_2_item3c_forward_collector import spacing_gap_diagnostics, spacing_gap_source_evidence, merge_observed_m5_rows

class Item3CGapDiagnosticsTest(unittest.TestCase):
    def test_exact_grid_has_no_diagnostics(self):
        t=datetime.fromisoformat("2026-09-29T09:00:00-03:00")
        rows=[{"timestamp":(t+timedelta(minutes=5*i)).isoformat()} for i in range(4)]
        self.assertEqual(spacing_gap_diagnostics(rows),[])

    def test_internal_missing_slot_is_reported_without_reconstruction(self):
        rows=[
            {"timestamp":"2026-09-29T09:00:00-03:00"},
            {"timestamp":"2026-09-29T09:05:00-03:00"},
            {"timestamp":"2026-09-29T09:15:00-03:00"},
        ]
        d=spacing_gap_diagnostics(rows)
        self.assertEqual(len(d),1)
        self.assertEqual(d[0]["observed_spacing_seconds"],600)
        self.assertEqual(d[0]["missing_m5_slots"],1)
        self.assertEqual(d[0]["after"],"2026-09-29T09:05:00-03:00")
        self.assertEqual(d[0]["before"],"2026-09-29T09:15:00-03:00")
        ev=spacing_gap_source_evidence(rows)
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["after_observed_row"]["timestamp"],"2026-09-29T09:05:00-03:00")
        self.assertEqual(ev[0]["before_observed_row"]["timestamp"],"2026-09-29T09:15:00-03:00")
        self.assertNotIn("2026-09-29T09:10:00-03:00", str(ev))

    def test_range_read_can_add_only_broker_observed_bar(self):
        base = [
            {"timestamp":"2026-10-09T18:20:00-03:00","close":1},
            {"timestamp":"2026-10-09T18:30:00-03:00","close":3},
        ]
        actual = {"timestamp":"2026-10-09T18:25:00-03:00","close":2}
        self.assertEqual(merge_observed_m5_rows(base, []), base)
        self.assertEqual(merge_observed_m5_rows(base, [base[0], actual]),
                         [base[0], actual, base[1]])
        with self.assertRaisesRegex(RuntimeError, "MT5_M5_SOURCE_CONFLICT"):
            merge_observed_m5_rows(base, [{"timestamp":base[0]["timestamp"],"close":99}])

if __name__=="__main__":
    unittest.main()
