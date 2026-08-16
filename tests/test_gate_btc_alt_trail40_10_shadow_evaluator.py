import json
import tempfile
import unittest
from pathlib import Path

from tools import gate_btc_alt_trail40_10_shadow_evaluator as evaluator


CONTRACT = {
    "schema": "gate_btc.alt_trail40_10_shadow_contract.v1",
    "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
    "candidate_definition": {
        "activation_gain": 0.40,
        "trailing_buffer_fraction_of_running_close_high": 0.10,
        "same_bar_arm_and_exit": False,
        "parameter_retuning_before_gate": False,
    },
    "prospective_gate": {
        "freeze_date": "2026-08-12",
        "evaluation_cohort": "ARMED_COMPLETED_JOURNEYS",
        "minimum_armed_completed_journeys": 30,
        "minimum_calendar_days_since_freeze": 120,
        "bootstrap_reps": 200,
        "bootstrap_seed": 20260812,
        "trim_top_positive_fraction": 0.05,
        "max_single_case_positive_benefit_share": 0.20,
        "requirements_all": [
            "execution_aware_mean_advantage_gt_0",
            "median_advantage_gt_0",
            "paired_bootstrap_95pct_ci_low_gt_0",
            "aggregate_benefit_gt_aggregate_regret",
            "mean_advantage_after_removing_top_5pct_positive_cases_gt_0",
            "no_single_case_dominates_total_positive_benefit",
        ],
    },
    "first_eligible_signal_date": "2026-08-31",
    "research_only": True,
    "engine_feed": False,
}


def signals(signal_date, execution_date, asset):
    out = {}
    for strategy in ("QOS_Moderada", "QOS_Ultra"):
        out[strategy] = {
            "strategy": strategy,
            "signal_date": signal_date,
            "signal_period": signal_date[:7],
            "execution_eligible_from": execution_date,
            "regime": "RISK_ON",
            "picks": [{"asset": asset, "weight": 0.1}],
        }
    return out


def make_row(day, sigs, closes, contract_sha, previous_sha):
    row = {
        "schema": "gate_btc.alt_trail40_10_shadow_daily.v1",
        "snapshot_date": day,
        "source_run_id": day,
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "signals": sigs,
        "selected_alt_closes": closes,
        "rollover_exit_assets": [],
        "current_portfolios_sha256": "p",
        "master_daily_sha256": "m",
        "previous_row_sha256": previous_sha,
        "contract_sha256": contract_sha,
        "economics_opened": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    row["row_sha256"] = evaluator.payload_sha(row, "row_sha256")
    return row


class AltTrailShadowEvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = self.root / "ledger"
        (self.ledger / "snapshots").mkdir(parents=True)
        self.contract = self.root / "contract.json"
        self.contract.write_text(json.dumps(CONTRACT), encoding="utf-8")
        contract_sha = evaluator.file_sha(self.contract)
        (self.ledger / "ANCHOR.json").write_text(json.dumps({
            "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
            "contract_sha256": contract_sha,
        }), encoding="utf-8")

        old = signals("2026-08-31", "2026-09-01", "SOL")
        new = signals("2026-09-05", "2026-09-06", "AVAX")
        rows = [
            ("2026-08-31", old, {}),
            ("2026-09-01", old, {"SOL": 100.0}),
            ("2026-09-02", old, {"SOL": 140.0}),
            ("2026-09-03", old, {"SOL": 150.0}),
            ("2026-09-04", old, {"SOL": 134.0}),
            ("2026-09-05", new, {"SOL": 130.0}),
            ("2026-09-06", new, {"SOL": 120.0, "AVAX": 30.0}),
        ]
        prev = None
        for day, sigs, closes in rows:
            value = make_row(day, sigs, closes, contract_sha, prev)
            if day in {"2026-09-05", "2026-09-06"}:
                value["rollover_exit_assets"] = ["SOL"]
                value["row_sha256"] = evaluator.payload_sha(value, "row_sha256")
            (self.ledger / f"snapshots/{day}.json").write_text(json.dumps(value), encoding="utf-8")
            prev = value["row_sha256"]

    def tearDown(self):
        self.temp.cleanup()

    def test_rule_arms_then_triggers_then_exits_next_bar(self):
        result = evaluator.evaluate(self.contract, self.ledger)
        trades = json.loads((self.ledger / "TRADES.json").read_text(encoding="utf-8"))
        trade = next(t for t in trades if t["strategy"] == "QOS_Moderada" and t["asset"] == "SOL")
        self.assertTrue(trade["completed"])
        self.assertTrue(trade["armed"])
        self.assertEqual(trade["arm_date"], "2026-09-02")
        self.assertEqual(trade["trigger_date"], "2026-09-04")
        self.assertEqual(trade["candidate_exit_date"], "2026-09-05")
        self.assertEqual(trade["control_exit_date"], "2026-09-06")
        self.assertAlmostEqual(trade["candidate_return"], 0.30, places=10)
        self.assertAlmostEqual(trade["control_return"], 0.20, places=10)
        self.assertAlmostEqual(trade["advantage"], 0.10, places=10)
        self.assertEqual(trade["outcome"], "HELPED")
        self.assertEqual(trade["recovery"], "NON_RECOVERED")
        self.assertEqual(result["armed_completed_journeys"], 2)
        self.assertEqual(result["decision"], "WAITING_PROSPECTIVE_GATE")

    def test_arming_bar_cannot_also_trigger(self):
        evaluator.evaluate(self.contract, self.ledger)
        trades = json.loads((self.ledger / "TRADES.json").read_text(encoding="utf-8"))
        trade = next(t for t in trades if t["strategy"] == "QOS_Ultra" and t["asset"] == "SOL")
        self.assertEqual(trade["arm_date"], "2026-09-02")
        self.assertNotEqual(trade["trigger_date"], trade["arm_date"])

    def test_broken_hash_chain_fails_closed(self):
        path = self.ledger / "snapshots/2026-09-03.json"
        row = json.loads(path.read_text(encoding="utf-8"))
        row["previous_row_sha256"] = "broken"
        row["row_sha256"] = evaluator.payload_sha(row, "row_sha256")
        path.write_text(json.dumps(row), encoding="utf-8")
        with self.assertRaises(RuntimeError):
            evaluator.evaluate(self.contract, self.ledger)


if __name__ == "__main__":
    unittest.main()
