import sys
import unittest
from pathlib import Path

import pandas as pd

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import gate_btc_profit_retention_study as study


class ProfitRetentionStudyTests(unittest.TestCase):
    def _prices(self):
        dates = pd.date_range("2026-01-31", periods=32, freq="D")
        vals = [100, 110, 120, 140, 125, 118] + [118] * 26
        return pd.Series(vals, index=dates, dtype=float)

    def test_policy_set_is_predeclared_and_exact(self):
        self.assertEqual(study.POLICIES, (
            "MONTH_END", "FIXED_7D", "FIXED_14D", "FIXED_21D",
            "LOCK_25", "LOCK_50", "LOCK_75",
        ))
        self.assertEqual(study.LOCK_ACTIVATION_GAIN, 0.20)

    def test_lock_50_measures_giveback_of_profit_not_price(self):
        p = self._prices()
        signal = p.index[0]
        boundary = p.index[-1]
        date, ret = study.policy_exit(p, signal, boundary, "LOCK_50")
        self.assertEqual(date, pd.Timestamp("2026-02-05"))
        self.assertAlmostEqual(ret, 0.18, places=12)

    def test_lock_never_stops_loss_before_activation(self):
        dates = pd.date_range("2026-01-31", periods=5, freq="D")
        prices = pd.Series([100, 80, 85, 90, 95], index=dates, dtype=float)
        date, ret = study.policy_exit(prices, dates[0], dates[-1], "LOCK_25")
        self.assertEqual(date, dates[-1])
        self.assertAlmostEqual(ret, -0.05, places=12)

    def test_fixed_horizon_uses_first_close_on_or_after_calendar_day(self):
        dates = pd.to_datetime(["2026-01-31", "2026-02-01", "2026-02-08", "2026-02-28"])
        prices = pd.Series([100, 101, 110, 120], index=dates, dtype=float)
        date, ret = study.policy_exit(prices, dates[0], dates[-1], "FIXED_7D")
        self.assertEqual(date, pd.Timestamp("2026-02-08"))
        self.assertAlmostEqual(ret, 0.10, places=12)

    def test_last_signal_without_next_boundary_is_excluded(self):
        selections = pd.DataFrame([
            {"signal_date":"2026-01-31","strategy":"QOS_Moderada","regime":"RISK_ON","picks":"AAA"},
            {"signal_date":"2026-02-28","strategy":"QOS_Moderada","regime":"RISK_ON","picks":"AAA"},
        ])
        coverage = pd.DataFrame([
            {"signal_date":"2026-01-31","coverage_ratio":0.96,"gate_95":True},
            {"signal_date":"2026-02-28","coverage_ratio":0.96,"gate_95":True},
        ])
        history = pd.DataFrame({
            "date": pd.date_range("2026-01-31", "2026-02-28", freq="D"),
            "symbol": "AAA",
            "close_usd": 100.0,
        })
        trades = study.build_trades(selections, coverage, history)
        self.assertEqual(trades["signal_date"].nunique(), 1)
        self.assertEqual(set(trades["policy"]), set(study.POLICIES))


if __name__ == "__main__":
    unittest.main()
