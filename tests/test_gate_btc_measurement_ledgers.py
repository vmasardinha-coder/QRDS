import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from tools.gate_btc_measurement_ledgers import (
    append_lock,
    audit_d50,
    initialize_lock,
    load_json,
    safe_gateway,
)

CONTRACT = {
    "status": "FROZEN_READY_FOR_PROSPECTIVE_LEDGER",
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "orders": 0,
    "capital": 0,
    "promotion": "PROHIBITED",
    "control": {"name": "NO_LOCK_CONTROL"},
    "variants": {
        "LOCK25": {"arming_level_multiple": 1.25, "protected_share_of_accumulated_profit": 0.25,
                   "destination": "VIRTUAL_CASH", "retracement_trigger_pct": 0.10,
                   "double_counting_prohibited": True},
        "LOCK50": {"arming_level_multiple": 1.50, "protected_share_of_accumulated_profit": 0.50,
                   "destination": "VIRTUAL_CASH", "retracement_trigger_pct": 0.15,
                   "double_counting_prohibited": True},
    },
    "cycle": {"reset_rule": "EXPLICIT_USER_DECISION_ONLY", "automatic_monthly_reset": False},
}


class MeasurementLedgerTests(unittest.TestCase):
    def test_gateway_same_source_close_is_not_double_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger"
            (ledger / "snapshots").mkdir(parents=True)
            manifest = root / "manifest.json"
            status = root / "status.json"
            comps = root / "comps.csv"
            profiles = root / "profiles.csv"
            manifest.write_text(json.dumps({"data_as_of": "2026-08-06"}), encoding="utf-8")
            status.write_text("{}", encoding="utf-8")
            comps.write_text("a\n1\n", encoding="utf-8")
            profiles.write_text("a\n1\n", encoding="utf-8")
            hashes = {p.name: __import__("hashlib").sha256(p.read_bytes()).hexdigest()
                      for p in (manifest, status, comps, profiles)}
            (ledger / "snapshots/2026-08-05.json").write_text(json.dumps({
                "snapshot_id": "2026-08-05", "data_as_of": "2026-08-06", "sequence": 1,
                "source_artifacts": hashes,
            }), encoding="utf-8")
            args = Namespace(manifest=manifest, snapshot_status=status, compositions=comps,
                             execution_profiles=profiles, snapshot_id="2026-08-06", ledger_dir=ledger)
            with patch("tools.gate_btc_measurement_common.append_gateway") as writer:
                self.assertEqual(safe_gateway(args), 0)
                writer.assert_not_called()

    def test_lock_anchor_and_two_hash_chained_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "contract.json"
            contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
            ledger = root / "ledger"
            init = Namespace(contract=contract, cycle_id="QOS_CURRENT_COMPOSITION_2026-08-06",
                             first_eligible_close="2026-08-06", ledger_dir=ledger)
            self.assertEqual(initialize_lock(init), 0)
            self.assertEqual(initialize_lock(init), 0)
            self.assertEqual(load_json(ledger / "STATUS.json")["valid_snapshot_count"], 0)

            equity = root / "equity.csv"
            portfolios = root / "portfolios.csv"
            portfolios.write_text(
                "data_as_of,signal_period,partial_period,execution_eligible_from,strategy,regime,asset,weight\n"
                "2026-08-06,2026-08,True,2026-08-06,QOS_Moderada,DEFENSIVE,BTC,1\n"
                "2026-08-06,2026-08,True,2026-08-06,QOS_Ultra,DEFENSIVE,BTC,1\n", encoding="utf-8")
            equity.write_text(
                "date,strategy,equity_brl,drawdown\n"
                "2026-08-06,QOS_Moderada,100,0\n"
                "2026-08-06,QOS_Ultra,200,0\n", encoding="utf-8")
            args = Namespace(contract=contract, equity_curves=equity, current_portfolios=portfolios,
                             snapshot_id="2026-08-06", cycle_id=init.cycle_id, ledger_dir=ledger)
            self.assertEqual(append_lock(args), 0)
            self.assertEqual(append_lock(args), 0)
            first = load_json(ledger / "snapshots/2026-08-06.json")
            self.assertEqual(len(first["rows"]), 6)
            self.assertTrue(all(row["previous_row_sha256"] is None for row in first["rows"]))

            equity.write_text(
                "date,strategy,equity_brl,drawdown\n"
                "2026-08-07,QOS_Moderada,130,0\n"
                "2026-08-07,QOS_Ultra,320,0\n", encoding="utf-8")
            args.snapshot_id = "2026-08-07"
            self.assertEqual(append_lock(args), 0)
            second = load_json(ledger / "snapshots/2026-08-07.json")
            self.assertEqual(second["sequence"], 2)
            self.assertTrue(all(row["previous_row_sha256"] for row in second["rows"]))
            mod25 = next(row for row in second["rows"]
                         if row["portfolio"] == "QOS_Moderada" and row["variant"] == "LOCK25")
            self.assertTrue(mod25["armed"])
            self.assertFalse(mod25["lock_triggered"])

    def test_lock_rejects_close_before_eligibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            contract = root / "contract.json"
            contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
            ledger = root / "ledger"
            initialize_lock(Namespace(contract=contract, cycle_id="cycle", first_eligible_close="2026-08-06", ledger_dir=ledger))
            equity = root / "equity.csv"
            portfolio = root / "portfolio.csv"
            equity.write_text("date,strategy,equity_brl,drawdown\n2026-08-05,QOS_Moderada,100,0\n2026-08-05,QOS_Ultra,200,0\n", encoding="utf-8")
            portfolio.write_text(
                "data_as_of,signal_period,partial_period,execution_eligible_from,strategy,regime,asset,weight\n"
                "2026-08-05,2026-08,True,2026-08-06,QOS_Moderada,DEFENSIVE,BTC,1\n"
                "2026-08-05,2026-08,True,2026-08-06,QOS_Ultra,DEFENSIVE,BTC,1\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                append_lock(Namespace(contract=contract, equity_curves=equity, current_portfolios=portfolio,
                                      snapshot_id="2026-08-05", cycle_id="cycle", ledger_dir=ledger))

    def test_d50_deep_diff_preserves_frozen_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen = root / "frozen.json"
            candidate = root / "candidate.json"
            output = root / "report.json"
            frozen.write_text('{"date":"2026-08-01","state":{"value":1}}', encoding="utf-8")
            candidate.write_text('{"date":"2026-08-01","state":{"value":2}}', encoding="utf-8")
            rc = audit_d50(Namespace(frozen_row=frozen, candidate_row=candidate, ignore_field=None, output=output))
            self.assertEqual(rc, 2)
            report = load_json(output)
            self.assertEqual(report["differences"][0]["path"], "$.state.value")
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(load_json(frozen)["state"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
