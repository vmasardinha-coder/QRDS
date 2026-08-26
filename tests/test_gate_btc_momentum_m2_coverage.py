import csv
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from tools.gate_btc_momentum_shadow_collect import compute_m2


class MomentumM2CoverageTests(unittest.TestCase):
    def _write_prices(self, rows):
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        p = root / "prices.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "asset", "close"])
            w.writeheader()
            w.writerows(rows)
        return td, p, root / "diag.json"

    @staticmethod
    def _days(n=40):
        start = date(2026, 7, 17)
        return [(start + timedelta(days=i)).isoformat() for i in range(n)]

    def test_union_extra_date_does_not_create_false_btc_gap(self):
        days = self._days(40)
        cutoff = days[-1]
        missing_btc = days[-10]
        rows = []
        for i, d in enumerate(days):
            if d != missing_btc:
                rows.append({"date": d, "asset": "BTC", "close": 100 + i})
            rows.append({"date": d, "asset": "ALT", "close": 50 + i * 0.5})
        td, p, diag = self._write_prices(rows)
        try:
            out, summary = compute_m2(p, cutoff, diag)
            payload = json.loads(diag.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS_COVERAGE")
            self.assertIn(missing_btc, payload["union_last_31_missing_from_btc"])
            self.assertEqual(summary["reference_calendar"], "BTC_COMPLETED_UTC_DAILY_BARS")
            self.assertEqual(summary["reference_window_bars"], 31)
            self.assertTrue(any(x["asset"] == "BTC" for x in out))
        finally:
            td.cleanup()

    def test_true_btc_cutoff_gap_fails_closed(self):
        days = self._days(40)
        cutoff = days[-1]
        rows = []
        for i, d in enumerate(days[:-1]):
            rows.append({"date": d, "asset": "BTC", "close": 100 + i})
        rows.append({"date": cutoff, "asset": "ALT", "close": 99})
        td, p, diag = self._write_prices(rows)
        try:
            with self.assertRaises(SystemExit):
                compute_m2(p, cutoff, diag)
            payload = json.loads(diag.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "DATA_GAP")
            self.assertEqual(payload["reason"], "BTC_CUTOFF_ABSENT")
        finally:
            td.cleanup()

    def test_candidate_missing_btc_reference_date_is_excluded_without_fill(self):
        days = self._days(40)
        cutoff = days[-1]
        rows = []
        missing_alt = days[-5]
        for i, d in enumerate(days):
            rows.append({"date": d, "asset": "BTC", "close": 100 + i})
            if d != missing_alt:
                rows.append({"date": d, "asset": "ALT", "close": 50 + i})
        td, p, diag = self._write_prices(rows)
        try:
            out, _ = compute_m2(p, cutoff, diag)
            payload = json.loads(diag.read_text(encoding="utf-8"))
            self.assertFalse(any(x["asset"] == "ALT" for x in out))
            alt_diag = next(x for x in payload["incomplete_assets"] if x["asset"] == "ALT")
            self.assertEqual(alt_diag["missing_reference_dates"], [missing_alt])
            self.assertFalse(payload["synthetic_backfill"])
        finally:
            td.cleanup()


if __name__ == "__main__":
    unittest.main()
