import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_prl50_position_shadow_archive as archive


CONTRACT = {
    "schema": "gate_btc.prl50_position_shadow_contract.v1",
    "candidate_name": "PRL50_POSITION",
    "candidate_definition": {"activation_gain": 0.20, "giveback_fraction_of_peak_profit": 0.50},
    "first_eligible_signal_date": "2026-08-31",
    "first_eligible_execution_date": "2026-09-01",
    "retrospective_backfill": "PROHIBITED",
    "name_collision_guard": {"must_remain_separate": True},
    "research_only": True,
    "engine_feed": False,
}


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def portfolios(signal="2026-08-31", execution="2026-09-01"):
    rows = []
    for strategy, picks in (("QOS_Moderada", ["SOL", "LINK"]), ("QOS_Ultra", ["SOL", "LINK", "AVAX"])):
        composition = [("BTC", 0.4), ("ETH", 0.2), ("CASH", 0.1)] + [(asset, 0.1) for asset in picks]
        for asset, weight in composition:
            rows.append({
                "strategy": strategy,
                "data_as_of": signal,
                "signal_period": signal[:7],
                "execution_eligible_from": execution,
                "regime": "RISK_ON",
                "asset": asset,
                "weight": weight,
            })
    return rows


class PRL50PositionShadowArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        self.contract = self.root / "contract.json"
        self.contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
        self.portfolios = self.root / "portfolios.csv"
        write_csv(self.portfolios, portfolios())
        self.master = self.root / "master.csv"
        write_csv(self.master, [
            {"date": "2026-08-31", "symbol": "SOL", "close_usd": "100"},
            {"date": "2026-08-31", "symbol": "LINK", "close_usd": "20"},
            {"date": "2026-08-31", "symbol": "AVAX", "close_usd": "30"},
            {"date": "2026-09-01", "symbol": "SOL", "close_usd": "101"},
            {"date": "2026-09-01", "symbol": "LINK", "close_usd": "21"},
            {"date": "2026-09-01", "symbol": "AVAX", "close_usd": "31"},
        ])
        archive.initialize(self.contract, self.ledger)

    def tearDown(self):
        self.temp.cleanup()

    def test_first_signal_then_entry_day(self):
        first = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        self.assertEqual(first["price_count"], 0)
        second = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-09-01", "2")
        self.assertEqual(second["price_count"], 3)
        row = json.loads((self.ledger / "snapshots/2026-09-01.json").read_text(encoding="utf-8"))
        self.assertEqual(row["selected_alt_closes"]["SOL"], 101.0)

    def test_late_first_record_fails_closed(self):
        with self.assertRaises(RuntimeError):
            archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-09-01", "2")

    def test_daily_gap_fails_closed(self):
        archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        with self.assertRaises(RuntimeError):
            archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-09-02", "3")

    def test_midcycle_pre_freeze_signal_fails_closed(self):
        write_csv(self.portfolios, portfolios("2026-07-31", "2026-08-01"))
        with self.assertRaises(RuntimeError):
            archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")

    def test_duplicate_identical_is_idempotent(self):
        first = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        duplicate = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        self.assertEqual(first["result"], "APPENDED")
        self.assertEqual(duplicate["result"], "DUPLICATE_IDENTICAL")


if __name__ == "__main__":
    unittest.main()
