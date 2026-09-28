import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools import gate_btc_alt_trail40_10_cycle as cycle
from tools import gate_btc_alt_trail40_10_shadow_archive as archive
from tools import gate_btc_alt_trail40_10_delivery_audit as legacy


def csv_file(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def portfolios(signal, execution):
    return [{"strategy": strategy, "data_as_of": signal, "signal_period": signal[:7],
             "execution_eligible_from": execution, "regime": "RISK_ON",
             "asset": "SOL", "weight": "0.3"} for strategy in archive.STRATEGIES]


class IndependentAltCycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "ledger"
        archive.initialize(cycle.BASE, self.root)
        self.anchor = (self.root / "ANCHOR.json").read_bytes()
        row = {"snapshot_date": "2026-08-31", "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
               "contract_sha256": archive.file_sha(cycle.BASE), "previous_row_sha256": None,
               "signals": {}, "selected_alt_closes": {}, "research_only": True}
        row["row_sha256"] = archive.payload_sha(row, "row_sha256")
        archive.write_json(self.root / "snapshots/2026-08-31.json", row)
        archive.write_json(self.root / "EVALUATION.json", {"decision": "WAITING_PROSPECTIVE_GATE"})
        self.original_snapshot = (self.root / "snapshots/2026-08-31.json").read_bytes()
        self.original_evaluation = (self.root / "EVALUATION.json").read_bytes()
        self.early = datetime(2026, 9, 28, 23, tzinfo=timezone.utc)
        self.first = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
        self.second = datetime(2026, 10, 2, 12, tzinfo=timezone.utc)
        self.port = Path(self.temp.name) / "port.csv"
        self.master = Path(self.temp.name) / "master.csv"
        csv_file(self.master, [{"date": "2026-09-30", "symbol": "SOL", "close_usd": "100"},
                               {"date": "2026-10-01", "symbol": "SOL", "close_usd": "105"}])

    def test_calendar_wait_and_sealed_original(self):
        state = cycle.plan(self.root, self.early)
        self.assertEqual(state["status"], "WAITING_APPROVED_MONTH_END_2026_09_30")
        self.assertFalse(state["can_append"])
        self.assertEqual(state["gate_minimum_calendar_days"], 120)
        self.assertEqual(state["gate_minimum_armed_completed_journeys"], 30)
        self.assertEqual(state["legacy_economic_credit"], 0)
        self.assertEqual(state["earliest_calendar_gate_date"], "2027-01-28")
        self.assertEqual((self.root / "ANCHOR.json").read_bytes(), self.anchor)
        self.assertEqual((self.root / "snapshots/2026-08-31.json").read_bytes(), self.original_snapshot)
        self.assertEqual((self.root / "EVALUATION.json").read_bytes(), self.original_evaluation)
        self.assertEqual(len(archive.snapshot_paths(self.root)), 1)

    def test_first_signal_and_held_monthly_entry(self):
        self.assertEqual(cycle.plan(self.root, self.first)["next_required_cutoff"], "2026-09-30")
        csv_file(self.port, portfolios("2026-09-30", "2026-10-01"))
        with self.assertRaisesRegex(ValueError, "SOURCE_CUTOFF_MISMATCH"):
            cycle.process(self.root, self.first, self.port, self.master, "2026-09-29", "42")
        first = cycle.process(self.root, self.first, self.port, self.master, "2026-09-30", "42")
        self.assertEqual(first["append"]["price_count"], 0)
        self.assertFalse(first["delivery"]["economic_result_valid"])
        csv_file(self.port, portfolios("2026-10-01", "2026-10-02"))
        second = cycle.process(self.root, self.second, self.port, self.master, "2026-10-01", "43")
        self.assertEqual(second["append"]["price_count"], 1)
        self.assertEqual(second["delivery"]["snapshot_count"], 2)
        self.assertEqual(second["delivery"]["armed_completed_journeys"], 0)
        row = archive.load_json(self.root / "epochs/monthly_20260930/snapshots/2026-10-01.json")
        self.assertEqual(row["signals"]["QOS_Moderada"]["signal_date"], "2026-09-30")
        self.assertEqual(row["observed_signals"]["QOS_Moderada"]["signal_date"], "2026-10-01")
        self.assertEqual((self.root / "ANCHOR.json").read_bytes(), self.anchor)
        self.assertEqual((self.root / "snapshots/2026-08-31.json").read_bytes(), self.original_snapshot)

    def test_missed_first_cutoff_cannot_be_backfilled(self):
        state = cycle.plan(self.root, self.second)
        self.assertEqual(state["status"], "FAILED_MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL")
        self.assertFalse(state["can_append"])
        self.assertEqual(state["next_required_cutoff"], "2026-09-30")


if __name__ == "__main__":
    unittest.main()
