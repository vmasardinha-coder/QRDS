import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools import gate_btc_prl50_position_cycle as cycle
from tools import gate_btc_prl50_position_economics as econ
from tools import gate_btc_prl50_position_shadow_archive as archive


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


class AuthorizedCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "prl50"
        archive.initialize(cycle.BASE, self.root)
        self.original = (self.root / "ANCHOR.json").read_bytes()
        econ.save(self.root / "INTERRUPTION.json", {
            "reason": "MISSING_FROZEN_MONTHLY_SIGNALS",
            "preserved_files_sha256": {"ANCHOR.json": econ.sha(self.root / "ANCHOR.json")}
        })
        self.early = datetime(2026, 9, 28, 23, tzinfo=timezone.utc)
        self.ready = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)

    def test_calendar_wait_authorizes_without_old_credit(self):
        status = cycle.plan(self.root, self.early)
        self.assertEqual(status["status"], "WAITING_APPROVED_MONTH_END_2026_09_30")
        self.assertFalse(status["can_append"])
        self.assertEqual(status["legacy_economic_credit"], 0)
        self.assertEqual(status["snapshot_count"], 0)
        self.assertEqual((self.root / "ANCHOR.json").read_bytes(), self.original)
        self.assertEqual(cycle.plan(self.root, self.ready)["next_required_cutoff"], "2026-09-30")

    def test_first_exact_signal_and_no_midcycle_start(self):
        self.assertEqual(cycle.plan(self.root, self.ready)["status"], "NEEDS_CURRENT_SOURCE")
        portfolios = Path(self.tmp.name) / "portfolios.csv"
        master = Path(self.tmp.name) / "master.csv"
        rows = []
        for strategy in archive.STRATEGIES:
            rows.append({"strategy": strategy, "data_as_of": "2026-09-30",
                         "signal_period": "2026-09", "execution_eligible_from": "2026-10-01",
                         "regime": "RISK_ON", "asset": "SOL", "weight": "0.3"})
        write_csv(portfolios, rows)
        write_csv(master, [{"date": "2026-09-30", "symbol": "SOL", "close_usd": "100"}])
        with self.assertRaisesRegex(ValueError, "SOURCE_CUTOFF_MISMATCH"):
            cycle.process(self.root, self.ready, portfolios, master, "2026-09-29", "123")
        result = cycle.process(self.root, self.ready, portfolios, master, "2026-09-30", "123")
        self.assertEqual(result["append"]["price_count"], 0)
        self.assertEqual(result["delivery"]["snapshot_count"], 1)
        self.assertFalse(result["delivery"]["economic_result_valid"])
        self.assertEqual((self.root / "ANCHOR.json").read_bytes(), self.original)
        self.assertEqual(len(archive.snapshot_paths(self.root)), 0)

    def test_missing_first_daily_close_is_fail_closed(self):
        later = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
        result = cycle.plan(self.root, later)
        self.assertEqual(result["status"], "FAILED_MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL")
        self.assertFalse(result["can_append"])
        self.assertEqual(result["next_required_cutoff"], "2026-09-30")


if __name__ == "__main__":
    unittest.main()
