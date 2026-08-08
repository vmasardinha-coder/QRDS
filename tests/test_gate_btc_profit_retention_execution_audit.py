import unittest

import pandas as pd

from tools import gate_btc_profit_retention_execution_audit as audit


class ProfitRetentionExecutionAuditTests(unittest.TestCase):
    def test_next_bar_entry_and_exit(self):
        index = pd.to_datetime([
            "2026-01-31", "2026-02-01", "2026-02-02", "2026-02-03",
            "2026-02-04", "2026-02-28", "2026-03-01",
        ])
        series = pd.Series([100, 100, 125, 130, 112, 110, 111], index=index, dtype=float)
        outcome = audit.trade_outcome(series, pd.Timestamp("2026-01-31"), pd.Timestamp("2026-02-28"))
        self.assertEqual(outcome["entry_date"], pd.Timestamp("2026-02-01"))
        self.assertEqual(outcome["trigger_date"], pd.Timestamp("2026-02-04"))
        self.assertEqual(outcome["lock50_exec_exit_date"], pd.Timestamp("2026-02-28"))
        self.assertEqual(outcome["baseline_exit_date"], pd.Timestamp("2026-03-01"))

    def test_no_trigger_uses_month_end_next_bar(self):
        index = pd.to_datetime(["2026-01-31", "2026-02-01", "2026-02-10", "2026-02-28", "2026-03-01"])
        series = pd.Series([100, 100, 110, 115, 116], index=index, dtype=float)
        outcome = audit.trade_outcome(series, pd.Timestamp("2026-01-31"), pd.Timestamp("2026-02-28"))
        self.assertIsNone(outcome["trigger_date"])
        self.assertEqual(outcome["lock50_exec_exit_date"], pd.Timestamp("2026-03-01"))
        self.assertAlmostEqual(outcome["lock50_exec_return"], outcome["baseline_return"])

    def test_giveback_is_fraction_of_peak_profit_not_price_drawdown(self):
        index = pd.to_datetime(["2026-01-31", "2026-02-01", "2026-02-02", "2026-02-03", "2026-03-01"])
        series = pd.Series([100, 100, 140, 119, 122], index=index, dtype=float)
        outcome = audit.trade_outcome(series, pd.Timestamp("2026-01-31"), pd.Timestamp("2026-02-28"))
        self.assertEqual(outcome["trigger_date"], pd.Timestamp("2026-02-03"))

    def test_pre_activation_loss_does_not_stop(self):
        index = pd.to_datetime(["2026-01-31", "2026-02-01", "2026-02-02", "2026-02-28", "2026-03-01"])
        series = pd.Series([100, 100, 70, 80, 81], index=index, dtype=float)
        outcome = audit.trade_outcome(series, pd.Timestamp("2026-01-31"), pd.Timestamp("2026-02-28"))
        self.assertIsNone(outcome["trigger_date"])


if __name__ == "__main__":
    unittest.main()
