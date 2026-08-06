import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from tools.gate_btc_measurement_ledgers import (
    append_lock, audit_d50, initialize_lock, initialize_source_anchor,
    load_json, safe_gateway,
)

CONTRACT = {
    "status": "FROZEN_READY_FOR_PROSPECTIVE_LEDGER",
    "research_only": True, "shadow_only": True, "not_approved": True,
    "orders": 0, "capital": 0, "promotion": "PROHIBITED",
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
CONFIG = {
    "execution_lag_daily_bars": 1,
    "exclude_partial_current_month_from_backtest": True,
    "stable_return_annual": 0.0,
    "fee_bps_per_rebalance_trade": 10,
    "slippage_bps_per_rebalance_trade": 15,
}


def current_signal(day: str, eligible: str, btc_weight: float = 1.0) -> str:
    cash = 1.0 - btc_weight
    rows = ["data_as_of,signal_period,partial_period,execution_eligible_from,strategy,regime,asset,weight"]
    for strategy in ("QOS_Moderada", "QOS_Ultra"):
        rows.append(f"{day},2026-08,True,{eligible},{strategy},DEFENSIVE,BTC,{btc_weight}")
        if cash:
            rows.append(f"{day},2026-08,True,{eligible},{strategy},DEFENSIVE,CASH,{cash}")
    return "\n".join(rows) + "\n"


class MeasurementLedgerTests(unittest.TestCase):
    def test_gateway_same_source_close_is_not_double_counted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); ledger = root / "ledger"; (ledger / "snapshots").mkdir(parents=True)
            manifest, status, comps, profiles = (root / n for n in ("manifest.json", "status.json", "comps.csv", "profiles.csv"))
            manifest.write_text(json.dumps({"data_as_of": "2026-08-06"})); status.write_text("{}")
            comps.write_text("a\n1\n"); profiles.write_text("a\n1\n")
            import hashlib
            hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (manifest, status, comps, profiles)}
            (ledger / "snapshots/2026-08-05.json").write_text(json.dumps({
                "snapshot_id": "2026-08-05", "data_as_of": "2026-08-06", "sequence": 1,
                "source_artifacts": hashes,
            }))
            args = Namespace(manifest=manifest, snapshot_status=status, compositions=comps,
                             execution_profiles=profiles, snapshot_id="2026-08-06", ledger_dir=ledger)
            with patch("tools.gate_btc_measurement_common.append_gateway") as writer:
                self.assertEqual(safe_gateway(args), 0); writer.assert_not_called()

    def _fixture(self, root: Path):
        contract = root / "contract.json"; contract.write_text(json.dumps(CONTRACT))
        config = root / "config.json"; config.write_text(json.dumps(CONFIG))
        monthly = root / "monthly.csv"
        monthly.write_text(
            "signal_date,execution_date,strategy,asset,weight,regime\n"
            "2026-07-31,2026-08-01,QOS_Moderada,BTC,0.5,DEFENSIVE\n"
            "2026-07-31,2026-08-01,QOS_Moderada,CASH,0.5,DEFENSIVE\n"
            "2026-07-31,2026-08-01,QOS_Ultra,BTC,0.5,DEFENSIVE\n"
            "2026-07-31,2026-08-01,QOS_Ultra,CASH,0.5,DEFENSIVE\n")
        equity = root / "equity.csv"
        equity.write_text("date,strategy,equity_brl,drawdown\n2026-08-05,QOS_Moderada,100,0\n2026-08-05,QOS_Ultra,200,0\n")
        initial = root / "initial.csv"; initial.write_text(current_signal("2026-08-05", "2026-08-06"))
        master = root / "master.csv"
        master.write_text(
            "date,symbol,close_usd,volume_usd,source\n"
            "2026-08-05,BTC,100,1,test\n"
            "2026-08-06,BTC,130,1,test\n"
            "2026-08-07,BTC,114.4,1,test\n"
            "2026-08-08,BTC,114.4,1,test\n"
            "2026-08-09,BTC,114.4,1,test\n")
        ledger = root / "ledger"
        initialize_lock(Namespace(contract=contract, cycle_id="QOS_CURRENT_COMPOSITION_2026-08-06",
                                  first_eligible_close="2026-08-06", ledger_dir=ledger))
        source_args = Namespace(contract=contract, current_portfolios=initial, monthly_allocations=monthly,
                                equity_curves=equity, v2a_config=config, base_date="2026-08-05",
                                cycle_id="QOS_CURRENT_COMPOSITION_2026-08-06", ledger_dir=ledger)
        initialize_source_anchor(source_args); initialize_source_anchor(source_args)
        return contract, master, ledger

    def _append(self, root, contract, master, ledger, day, eligible):
        signal = root / f"signal-{day}.csv"; signal.write_text(current_signal(day, eligible))
        return append_lock(Namespace(contract=contract, master_daily=master, current_portfolios=signal,
                                     snapshot_id=day, cycle_id="QOS_CURRENT_COMPOSITION_2026-08-06",
                                     ledger_dir=ledger))

    def test_lock_tracks_live_composition_and_executes_next_bar(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); contract, master, ledger = self._fixture(root)
            self.assertEqual(load_json(ledger / "STATUS.json")["status"], "READY_WAITING_FIRST_ELIGIBLE_CLOSE")
            self.assertEqual(self._append(root, contract, master, ledger, "2026-08-06", "2026-08-07"), 0)
            first = load_json(ledger / "snapshots/2026-08-06.json")
            self.assertEqual(len(first["rows"]), 6)
            control = next(r for r in first["rows"] if r["portfolio"] == "QOS_Moderada" and r["variant"] == "NO_LOCK_CONTROL")
            self.assertAlmostEqual(control["net_equity_after_lock"], 100 * (1 - 0.0025) * 1.30, places=9)
            lock25 = next(r for r in first["rows"] if r["portfolio"] == "QOS_Moderada" and r["variant"] == "LOCK25")
            self.assertTrue(lock25["armed"]); self.assertFalse(lock25["lock_triggered"])

            self._append(root, contract, master, ledger, "2026-08-07", "2026-08-08")
            second = load_json(ledger / "snapshots/2026-08-07.json")
            lock25 = next(r for r in second["rows"] if r["portfolio"] == "QOS_Moderada" and r["variant"] == "LOCK25")
            self.assertTrue(lock25["lock_triggered"])
            self.assertTrue(lock25["lock_execution_pending"])
            self.assertEqual(lock25["protected_cash_after"], 0)

            self._append(root, contract, master, ledger, "2026-08-08", "2026-08-09")
            third = load_json(ledger / "snapshots/2026-08-08.json")
            lock25 = next(r for r in third["rows"] if r["portfolio"] == "QOS_Moderada" and r["variant"] == "LOCK25")
            self.assertTrue(lock25["lock_execution_applied"])
            self.assertGreater(lock25["protected_cash_after"], 0)
            self.assertTrue(lock25["reentry_execution_pending"])

            self._append(root, contract, master, ledger, "2026-08-09", "2026-08-10")
            fourth = load_json(ledger / "snapshots/2026-08-09.json")
            lock25 = next(r for r in fourth["rows"] if r["portfolio"] == "QOS_Moderada" and r["variant"] == "LOCK25")
            self.assertTrue(lock25["reentry_execution_applied"])
            self.assertEqual(lock25["protected_cash_after"], 0)
            self.assertEqual(load_json(ledger / "STATUS.json")["valid_snapshot_count"], 4)

    def test_lock_duplicate_must_be_byte_equivalent_and_gaps_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); contract, master, ledger = self._fixture(root)
            self._append(root, contract, master, ledger, "2026-08-06", "2026-08-07")
            self.assertEqual(self._append(root, contract, master, ledger, "2026-08-06", "2026-08-07"), 0)
            with self.assertRaises(RuntimeError):
                self._append(root, contract, master, ledger, "2026-08-08", "2026-08-09")

    def test_d50_deep_diff_preserves_frozen_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); frozen = root / "frozen.json"; candidate = root / "candidate.json"; output = root / "report.json"
            frozen.write_text('{"date":"2026-08-01","state":{"value":1}}')
            candidate.write_text('{"date":"2026-08-01","state":{"value":2}}')
            rc = audit_d50(Namespace(frozen_row=frozen, candidate_row=candidate, ignore_field=None, output=output))
            self.assertEqual(rc, 2)
            report = load_json(output)
            self.assertEqual(report["differences"][0]["path"], "$.state.value")
            self.assertFalse(report["mutation_performed"])
            self.assertEqual(load_json(frozen)["state"]["value"], 1)


if __name__ == "__main__":
    unittest.main()
