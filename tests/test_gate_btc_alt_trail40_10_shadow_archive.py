import csv
import json
import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_alt_trail40_10_shadow_archive as archive


CONTRACT = {
    "schema": "gate_btc.alt_trail40_10_shadow_contract.v1",
    "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
    "candidate_definition": {
        "activation_gain": 0.40,
        "trailing_buffer_fraction_of_running_close_high"] if False else 0.10,
        "same_bar_arm_and_exit": False,
        "parameter_retuning_before_gate": False,
    },
    "eligible_assets": "ALT_PICKS_ONLY_EXCLUDING_BTC_ETH_BNB_CASH",
    "first_eligible_signal_date": "2026-08-31",
    "first_eligible_execution_date": "2026-09-01",
    "retrospective_backfill": "PROHIBITED",
    "historical_evidence_freeze": {
        "qos_crosscheck": {
            "decision": "HISTORICALLY_REJECTED_OR_INSUFFICIENT_FOR_PROMOTION",
            "rule_search_status": "CLOSED_NO_RETUNING_ON_THIS_SAMPLE",
        }
    },
    "research_only": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
}


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def portfolios(signal="2026-08-31", execution="2026-09-01"):
    rows = []
    for strategy, picks in (("QOS_Moderada", ["SOL", "LINK", "BNB"]), ("QOS_Ultra", ["SOL", "AVAX", "BNB"])):
        composition = [("BTC", 0.3), ("ETH", 0.2), ("CASH", 0.1)] + [(asset, 0.1) for asset in picks]
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


class AltTrailShadowArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        self.contract = self.root / "contract.json"
        self.contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
        self.portfolios = self.root / "portfolios.csv"
        write_csv(self.portfolios, portfolios())
        self.master = self.root / "master.csv"
        rows=[]
        for day, values in {
            "2026-08-31": {"SOL":100,"LINK":20,"AVAX":30,"BNB":900},
            "2026-09-01": {"SOL":101,"LINK":21,"AVAX":31,"BNB":910},
            "2026-09-02": {"SOL":102,"LINK":22,"AVAX":32,"BNB":920},
        }.items():
            for symbol, close in values.items():
                rows.append({"date":day,"symbol":symbol,"close_usd":str(close)})
        write_csv(self.master, rows)
        archive.initialize(self.contract, self.ledger)

    def tearDown(self):
        self.temp.cleanup()

    def test_first_signal_then_entry_day_and_bnb_excluded(self):
        first = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        self.assertEqual(first["price_count"], 0)
        second = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-09-01", "2")
        self.assertEqual(second["price_count"], 3)
        row = json.loads((self.ledger / "snapshots/2026-09-01.json").read_text(encoding="utf-8"))
        self.assertEqual(row["selected_alt_closes"]["SOL"], 101.0)
        self.assertNotIn("BNB", row["selected_alt_closes"])
        self.assertFalse(row["economics_opened"])

    def test_late_first_record_fails_closed(self):
        with self.assertRaises(RuntimeError):
            archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-09-01", "2")

    def test_daily_gap_is_recorded_without_backfill_and_current_day_continues(self):
        archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        result = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-09-02", "3")
        self.assertEqual(result["result"], "APPENDED_WITH_RECORDED_GAP")
        self.assertEqual(result["prospective_gap_dates"], ["2026-09-01"])
        self.assertFalse((self.ledger / "snapshots/2026-09-01.json").exists())
        row = json.loads((self.ledger / "snapshots/2026-09-02.json").read_text(encoding="utf-8"))
        self.assertEqual(row["prospective_gap_policy"], "RECORD_GAP_AND_CONTINUE_FORWARD_NO_BACKFILL")
        self.assertEqual(row["prospective_gap_dates"], ["2026-09-01"])

    def test_midcycle_pre_freeze_signal_fails_closed(self):
        write_csv(self.portfolios, portfolios("2026-07-31", "2026-08-01"))
        with self.assertRaises(RuntimeError):
            archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")

    def test_duplicate_identical_is_idempotent(self):
        first = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        duplicate = archive.append(self.contract, self.ledger, self.portfolios, self.master, "2026-08-31", "1")
        self.assertEqual(first["result"], "APPENDED")
        self.assertEqual(duplicate["result"], "DUPLICATE_IDENTICAL")

    def test_contract_parameter_drift_fails(self):
        bad = dict(CONTRACT)
        bad["candidate_definition"] = dict(CONTRACT["candidate_definition"])
        bad["candidate_definition"]["activation_gain"] = 0.35
        self.contract.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            archive.initialize(self.contract, self.root / "bad-ledger")


if __name__ == "__main__":
    unittest.main()
