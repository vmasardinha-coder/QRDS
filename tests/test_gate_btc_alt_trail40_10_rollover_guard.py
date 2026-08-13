import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_alt_trail40_10_rollover_guard as guard


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def signal(signal_date, execution_date, picks):
    return {
        "strategy": "",
        "signal_date": signal_date,
        "signal_period": signal_date[:7],
        "execution_eligible_from": execution_date,
        "regime": "RISK_ON",
        "picks": [{"asset": asset, "weight": 0.1} for asset in picks],
    }


def row(day, signals, closes, previous_sha):
    value = {
        "schema": "gate_btc.alt_trail40_10_shadow_daily.v1",
        "snapshot_date": day,
        "source_run_id": day,
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "signals": signals,
        "selected_alt_closes": closes,
        "current_portfolios_sha256": "p",
        "master_daily_sha256": "m",
        "previous_row_sha256": previous_sha,
        "contract_sha256": "c",
        "economics_opened": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    value["row_sha256"] = guard.payload_sha(value, "row_sha256")
    return value


class AltTrailRolloverGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        (self.ledger / "snapshots").mkdir(parents=True)
        self.master = self.root / "master.csv"
        write_csv(self.master, [
            {"date": "2026-09-30", "symbol": "SOL", "close_usd": "110"},
            {"date": "2026-09-30", "symbol": "LINK", "close_usd": "22"},
            {"date": "2026-09-30", "symbol": "BNB", "close_usd": "950"},
            {"date": "2026-10-01", "symbol": "SOL", "close_usd": "111"},
            {"date": "2026-10-01", "symbol": "LINK", "close_usd": "23"},
            {"date": "2026-10-01", "symbol": "AVAX", "close_usd": "35"},
            {"date": "2026-10-02", "symbol": "AVAX", "close_usd": "36"},
        ])

    def tearDown(self):
        self.temp.cleanup()

    def _signals(self, signal_date, execution_date, picks):
        return {
            "QOS_Moderada": {**signal(signal_date, execution_date, picks), "strategy": "QOS_Moderada"},
            "QOS_Ultra": {**signal(signal_date, execution_date, picks), "strategy": "QOS_Ultra"},
        }

    def _write_status(self, day, sha):
        (self.ledger / "STATUS.json").write_text(json.dumps({
            "latest_snapshot_date": day,
            "latest_row_sha256": sha,
        }), encoding="utf-8")

    def test_rollover_keeps_old_assets_through_new_execution_bar(self):
        old = row("2026-09-29", self._signals("2026-08-31", "2026-09-01", ["SOL", "LINK", "BNB"]), {"SOL": 109.0, "LINK": 21.0}, None)
        (self.ledger / "snapshots/2026-09-29.json").write_text(json.dumps(old), encoding="utf-8")

        change = row("2026-09-30", self._signals("2026-09-30", "2026-10-01", ["AVAX", "BNB"]), {}, old["row_sha256"])
        (self.ledger / "snapshots/2026-09-30.json").write_text(json.dumps(change), encoding="utf-8")
        self._write_status("2026-09-30", change["row_sha256"])

        result = guard.patch(self.ledger, self.master, "2026-09-30")
        self.assertEqual(result["rollover_assets"], ["LINK", "SOL"])
        patched = json.loads((self.ledger / "snapshots/2026-09-30.json").read_text(encoding="utf-8"))
        self.assertEqual(set(patched["selected_alt_closes"]), {"SOL", "LINK"})
        self.assertNotIn("BNB", patched["rollover_exit_assets"])

        next_row = row("2026-10-01", self._signals("2026-09-30", "2026-10-01", ["AVAX", "BNB"]), {"AVAX": 35.0}, patched["row_sha256"])
        (self.ledger / "snapshots/2026-10-01.json").write_text(json.dumps(next_row), encoding="utf-8")
        self._write_status("2026-10-01", next_row["row_sha256"])
        result2 = guard.patch(self.ledger, self.master, "2026-10-01")
        self.assertEqual(result2["rollover_assets"], ["LINK", "SOL"])
        exit_row = json.loads((self.ledger / "snapshots/2026-10-01.json").read_text(encoding="utf-8"))
        self.assertEqual(set(exit_row["selected_alt_closes"]), {"SOL", "LINK", "AVAX"})

        after = row("2026-10-02", self._signals("2026-09-30", "2026-10-01", ["AVAX", "BNB"]), {"AVAX": 36.0}, exit_row["row_sha256"])
        (self.ledger / "snapshots/2026-10-02.json").write_text(json.dumps(after), encoding="utf-8")
        self._write_status("2026-10-02", after["row_sha256"])
        result3 = guard.patch(self.ledger, self.master, "2026-10-02")
        self.assertEqual(result3["rollover_assets"], [])

    def test_missing_old_asset_exit_price_fails_closed(self):
        old = row("2026-09-29", self._signals("2026-08-31", "2026-09-01", ["SOL", "DOGE"]), {"SOL": 109.0, "DOGE": 0.2}, None)
        (self.ledger / "snapshots/2026-09-29.json").write_text(json.dumps(old), encoding="utf-8")
        change = row("2026-09-30", self._signals("2026-09-30", "2026-10-01", ["AVAX"]), {}, old["row_sha256"])
        (self.ledger / "snapshots/2026-09-30.json").write_text(json.dumps(change), encoding="utf-8")
        self._write_status("2026-09-30", change["row_sha256"])
        with self.assertRaises(RuntimeError):
            guard.patch(self.ledger, self.master, "2026-09-30")


if __name__ == "__main__":
    unittest.main()
