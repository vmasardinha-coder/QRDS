"""Testes offline do agente de trading (sem rede, dados sinteticos)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from trading_agent import config, portfolio, report, strategy


def flat_series(price: float, days: int) -> list[float]:
    return [price] * days


def trending_series(start: float, daily_ret: float, days: int) -> list[float]:
    out = [start]
    for _ in range(days - 1):
        out.append(out[-1] * (1 + daily_ret))
    return out


class TestStrategy(unittest.TestCase):
    def test_equity_momentum_prefers_uptrend(self):
        up = trending_series(100, 0.002, 300)
        down = trending_series(100, -0.002, 300)
        self.assertGreater(strategy.equity_momentum_score(up),
                           strategy.equity_momentum_score(down))

    def test_equity_momentum_requires_history(self):
        self.assertIsNone(strategy.equity_momentum_score(flat_series(100, 50)))

    def test_equity_targets_top_n_and_exposure(self):
        universe = {f"T{i}": trending_series(100, 0.0005 * (i + 1), 300)
                    for i in range(15)}
        bench_up = trending_series(100, 0.001, 300)
        weights, regime = strategy.equity_target_weights(universe, bench_up)
        self.assertEqual(regime, "risk_on")
        self.assertEqual(len(weights), config.EQUITY_TOP_N)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        # os melhores momentums (indices altos) devem estar selecionados
        self.assertIn("T14", weights)
        self.assertNotIn("T0", weights)

    def test_equity_risk_off_halves_exposure(self):
        universe = {f"T{i}": trending_series(100, 0.001, 300) for i in range(12)}
        bench_down = trending_series(100, -0.001, 300)
        weights, regime = strategy.equity_target_weights(universe, bench_down)
        self.assertEqual(regime, "risk_off")
        self.assertAlmostEqual(sum(weights.values()),
                               config.EQUITY_RISK_OFF_EXPOSURE, places=6)

    def test_crypto_all_btc_when_no_alt_beats_it(self):
        universe = {
            "BTC": trending_series(50_000, 0.002, 250),
            "ETH": trending_series(3_000, 0.0005, 250),
            "SOL": trending_series(150, -0.001, 250),
        }
        weights, regime = strategy.crypto_target_weights(universe)
        self.assertEqual(regime, "risk_on")
        self.assertEqual(set(weights), {"BTC"})
        self.assertAlmostEqual(weights["BTC"], 1.0, places=6)

    def test_crypto_tilts_into_stronger_alts(self):
        universe = {
            "BTC": trending_series(50_000, 0.001, 250),
            "ETH": trending_series(3_000, 0.003, 250),
            "SOL": trending_series(150, 0.004, 250),
            "ADA": trending_series(1, 0.0001, 250),
        }
        weights, _ = strategy.crypto_target_weights(universe)
        self.assertIn("ETH", weights)
        self.assertIn("SOL", weights)
        self.assertNotIn("ADA", weights)
        self.assertAlmostEqual(weights["BTC"], config.CRYPTO_BTC_CORE_WEIGHT, places=6)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(portfolio, "STATE_DIR", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_initial_buy_and_nav(self):
        state = portfolio.new_state("equities", "SPY", "2026-01-05", 500.0)
        prices = {"AAA": 100.0, "BBB": 50.0}
        orders = portfolio.build_orders(state, {"AAA": 0.5, "BBB": 0.5}, prices)
        trades = portfolio.execute_orders(state, orders, "2026-01-05", 0.0)
        self.assertEqual(len(trades), 2)
        self.assertAlmostEqual(portfolio.nav(state, prices),
                               config.INITIAL_CAPITAL_USD, delta=1.0)
        self.assertLess(state["cash"], 1.0)

    def test_slippage_costs_money(self):
        state = portfolio.new_state("equities", "SPY", "2026-01-05", 500.0)
        prices = {"AAA": 100.0}
        orders = portfolio.build_orders(state, {"AAA": 1.0}, prices)
        portfolio.execute_orders(state, orders, "2026-01-05", 100.0)  # 1%
        self.assertLess(portfolio.nav(state, prices),
                        config.INITIAL_CAPITAL_USD)

    def test_sell_frees_cash_before_buy(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        prices = {"AAA": 100.0, "BBB": 50.0}
        portfolio.execute_orders(
            state, portfolio.build_orders(state, {"AAA": 1.0}, prices),
            "2026-01-05", 0.0)
        orders = portfolio.build_orders(state, {"BBB": 1.0}, prices)
        self.assertEqual(orders[0]["side"], "sell")
        portfolio.execute_orders(state, orders, "2026-01-06", 0.0)
        self.assertNotIn("AAA", state["positions"])
        self.assertIn("BBB", state["positions"])

    def test_benchmark_history_tracks_ratio(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        entry = portfolio.append_history(state, "2026-01-06", {}, 550.0)
        self.assertAlmostEqual(entry["benchmark_nav"],
                               config.INITIAL_CAPITAL_USD * 1.1, places=2)

    def test_state_roundtrip(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        state["positions"]["AAA"] = {"qty": 2.5, "avg_cost": 10.0}
        portfolio.save_state(state)
        loaded = portfolio.load_state("x")
        self.assertEqual(loaded, json.loads(json.dumps(state)))

    def test_needs_rebalance_first_run_and_regime_change(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        self.assertTrue(portfolio.needs_rebalance(state, {}, {}, 2, "risk_on"))
        state["last_rebalance"] = "2026-01-05"
        state["last_regime"] = "risk_on"
        self.assertTrue(portfolio.needs_rebalance(state, {}, {}, 2, "risk_off"))
        self.assertFalse(portfolio.needs_rebalance(state, {}, {}, 2, "risk_on"))
        self.assertTrue(portfolio.needs_rebalance(state, {}, {}, 0, "risk_on"))


class TestReport(unittest.TestCase):
    def test_report_contains_key_sections(self):
        state = portfolio.new_state("equities", "SPY", "2026-01-05", 500.0)
        state["positions"] = {"AAA": {"qty": 100.0, "avg_cost": 100.0}}
        state["cash"] = 40_000.0
        state["history"] = [{"date": "2026-01-05", "nav": 50_000.0,
                             "benchmark_nav": 50_000.0}]
        result = {
            "state": state,
            "entry": state["history"][-1],
            "trades": [{"date": "2026-01-05", "symbol": "AAA", "side": "buy",
                        "qty": 100.0, "price": 100.0, "value": 10_000.0}],
            "regime": "risk_on",
            "targets": {"AAA": 0.2},
            "prices": {"AAA": 100.0},
            "rebalanced": True,
            "data_failures": [],
        }
        content = report.build_report("2026-01-05", {"equities": result},
                                      {"crypto": "sem rede"})
        self.assertIn("Acoes EUA", content)
        self.assertIn("AAA", content)
        self.assertIn("COMPRA", content)
        self.assertIn("Alfa vs SPY", content)
        self.assertIn("ERRO", content)


class TestB3(unittest.TestCase):
    def test_cdi_index_accumulates(self):
        from trading_agent import data_sources
        rates = [("2026-01-05", 0.05), ("2026-01-06", 0.05)]
        idx = data_sources.cdi_index(rates)
        self.assertAlmostEqual(idx[-1][1], 1.0005 * 1.0005, places=8)

    def test_cash_accrues_cdi(self):
        state = portfolio.new_state("b3", "^BVSP", "2026-01-05", 130_000.0,
                                    currency="BRL", initial_capital=50_000.0)
        rates = [("2026-01-05", 0.05), ("2026-01-06", 0.05), ("2026-01-07", 0.05)]
        portfolio.accrue_cash_cdi(state, rates, "2026-01-07")
        # so acumula dias APOS a inception (06 e 07)
        self.assertAlmostEqual(state["cash"], 50_000.0 * 1.0005 ** 2, places=4)
        self.assertEqual(state["last_accrual_date"], "2026-01-07")

    def test_b3_targets_use_top_n(self):
        universe = {f"T{i}": trending_series(10, 0.0004 * (i + 1), 300)
                    for i in range(12)}
        bench = trending_series(100_000, 0.001, 300)
        weights, regime = strategy.b3_target_weights(universe, bench)
        self.assertEqual(regime, "risk_on")
        self.assertEqual(len(weights), config.B3_TOP_N)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)


class TestStructured(unittest.TestCase):
    def test_bs_call_above_intrinsic_and_rises_with_vol(self):
        from trading_agent import structured
        low = structured.bs_call_price(100, 103, 30 / 365, 0.10, 0.15)
        high = structured.bs_call_price(100, 103, 30 / 365, 0.10, 0.40)
        self.assertGreater(high, low)
        self.assertGreater(low, 0.0)
        itm = structured.bs_call_price(110, 100, 0.0, 0.10, 0.20)
        self.assertAlmostEqual(itm, 10.0, places=6)

    def test_covered_call_cycle(self):
        from trading_agent import structured
        state = portfolio.new_state("b3_estruturadas", "^BVSP", "2026-01-05",
                                    130_000.0, currency="BRL",
                                    initial_capital=50_000.0)
        state["positions"]["BOVA11"] = {"qty": 500.0, "avg_cost": 100.0}
        state["cash"] = 0.0
        trade = structured.sell_new_call(state, 100.0, 0.25, 0.10, "2026-01-05")
        self.assertGreater(state["cash"], 0.0)
        self.assertEqual(trade["side"], "sell")
        sc = state["short_call"]
        self.assertAlmostEqual(sc["strike"], 103.0, places=2)
        # antes do vencimento nada liquida
        self.assertIsNone(structured.settle_expired_call(state, 110.0, "2026-01-20"))
        # no vencimento acima do strike paga a diferenca
        cash_before = state["cash"]
        settle = structured.settle_expired_call(state, 110.0, sc["expiry"])
        self.assertIsNotNone(settle)
        self.assertAlmostEqual(cash_before - state["cash"], (110.0 - 103.0) * 500.0,
                               places=2)
        self.assertIsNone(state["short_call"])

    def test_realized_vol_positive(self):
        from trading_agent import structured
        series = trending_series(100, 0.001, 60)
        vol = structured.realized_vol(series, 30)
        self.assertGreaterEqual(vol, 0.0)


if __name__ == "__main__":
    unittest.main()
