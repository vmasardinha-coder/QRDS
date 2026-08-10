"""Testes offline do agente de trading (sem rede, dados sinteticos).

Cobrem as regras da Carta de Operacao: teto por posicao, piso de
diversificacao, forca relativa ao benchmark, filtro de liquidez, stop
estatistico com carencia, integridade de dado e log auditavel.
"""

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


def as_series(closes: list[float], volume: float = 1_000_000.0):
    """Converte fechos em serie (data, fecho, volume) como as fontes devolvem."""
    return [(f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", c, volume)
            for i, c in enumerate(closes)]


class TestStrategy(unittest.TestCase):
    def test_equity_momentum_prefers_uptrend(self):
        up = trending_series(100, 0.002, 300)
        down = trending_series(100, -0.002, 300)
        self.assertGreater(strategy.equity_momentum_score(up),
                           strategy.equity_momentum_score(down))

    def test_equity_momentum_requires_history(self):
        self.assertIsNone(strategy.equity_momentum_score(flat_series(100, 50)))

    def test_relative_strength_rejects_below_benchmark(self):
        universe = {f"T{i}": as_series(trending_series(100, 0.0005 * (i + 1), 300))
                    for i in range(15)}
        bench = trending_series(100, 0.001, 300)
        decision = strategy.equity_decision(universe, bench)
        selected = {s["symbol"] for s in decision["selected"]}
        # T0 e T1 nao superam o benchmark -> rejeitados por forca relativa
        self.assertNotIn("T0", selected)
        self.assertNotIn("T1", selected)
        self.assertIn("T14", selected)
        reasons = {r["symbol"]: r["reason"] for r in decision["rejected"]}
        self.assertIn("nao bate o benchmark", reasons["T0"])

    def test_liquidity_filter_excludes_illiquid(self):
        universe = {f"T{i}": as_series(trending_series(100, 0.003, 300))
                    for i in range(8)}
        universe["ILIQ"] = as_series(trending_series(100, 0.009, 300), volume=1.0)
        bench = trending_series(100, 0.0005, 300)
        decision = strategy.equity_decision(universe, bench)
        selected = {s["symbol"] for s in decision["selected"]}
        # apesar do melhor momentum de todos, nao entra: nao e executavel
        self.assertNotIn("ILIQ", selected)
        reasons = {r["symbol"]: r["reason"] for r in decision["rejected"]}
        self.assertIn("liquidez baixa", reasons["ILIQ"])

    def test_equity_risk_off_halves_exposure(self):
        universe = {f"T{i}": as_series(trending_series(100, 0.002, 300))
                    for i in range(12)}
        bench_down = trending_series(100, -0.001, 300)
        decision = strategy.equity_decision(universe, bench_down)
        self.assertEqual(decision["regime"], "risk_off")
        self.assertAlmostEqual(sum(decision["weights"].values()),
                               config.EQUITY_RISK_OFF_EXPOSURE, places=6)

    def test_crypto_all_btc_when_no_alt_beats_it(self):
        universe = {
            "BTC": as_series(trending_series(50_000, 0.002, 250)),
            "ETH": as_series(trending_series(3_000, 0.0005, 250)),
            "SOL": as_series(trending_series(150, -0.001, 250)),
        }
        decision = strategy.crypto_decision(universe)
        self.assertEqual(set(decision["weights"]), {"BTC"})
        self.assertLessEqual(decision["weights"]["BTC"],
                             config.CRYPTO_BTC_ANCHOR_MAX)

    def test_crypto_alts_respect_position_cap(self):
        universe = {
            "BTC": as_series(trending_series(50_000, 0.001, 250)),
            "ETH": as_series(trending_series(3_000, 0.003, 250)),
            "SOL": as_series(trending_series(150, 0.004, 250)),
            "AVAX": as_series(trending_series(40, 0.005, 250)),
            "ADA": as_series(trending_series(1, 0.0001, 250)),
        }
        decision = strategy.crypto_decision(universe)
        weights = decision["weights"]
        self.assertNotIn("ADA", weights)
        for symbol, weight in weights.items():
            if symbol == "BTC":
                self.assertLessEqual(weight, config.CRYPTO_BTC_ANCHOR_MAX + 1e-9)
            else:
                self.assertLessEqual(weight,
                                     config.MAX_ACTIVE_POSITION_WEIGHT + 1e-9)


class TestCharterLimits(unittest.TestCase):
    def test_position_cap_never_exceeded_and_rest_stays_cash(self):
        ranked = [(f"T{i}", 0.5 - i * 0.01) for i in range(4)]
        weights, note = strategy.allocate(ranked, exposure=1.0, top_n=4,
                                          min_positions=3, max_weight=0.15)
        self.assertEqual(len(weights), 4)
        for weight in weights.values():
            self.assertAlmostEqual(weight, 0.15, places=9)
        # 4 x 15% = 60%; os restantes 40% ficam em caixa, nao sao redistribuidos
        self.assertAlmostEqual(sum(weights.values()), 0.60, places=9)
        self.assertIn("caixa", note)

    def test_diversification_floor_goes_to_cash(self):
        ranked = [("A", 0.4), ("B", 0.3)]
        weights, note = strategy.allocate(ranked, exposure=1.0, top_n=10,
                                          min_positions=5, max_weight=0.15)
        self.assertEqual(weights, {})
        self.assertIn("piso de diversificacao", note)

    def test_floor_is_not_loosened_by_weak_candidates(self):
        universe = {f"T{i}": as_series(trending_series(100, 0.003, 300))
                    for i in range(3)}
        bench = trending_series(100, 0.0005, 300)
        decision = strategy.equity_decision(universe, bench)
        # 3 candidatos validos < piso de 5 -> tudo em caixa
        self.assertEqual(decision["weights"], {})
        self.assertAlmostEqual(decision["cash_weight"], 1.0, places=6)


class TestStops(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(portfolio, "STATE_DIR", Path(self.tmp.name))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def _state_with_position(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        state["cash"] = 0.0
        state["positions"]["AAA"] = {"qty": 100.0, "avg_cost": 100.0,
                                     "high_water": 100.0}
        return state

    def test_daily_sigma_scales_with_volatility(self):
        calm = portfolio.daily_sigma(trending_series(100, 0.001, 100), 60)
        self.assertIsNotNone(calm)
        self.assertLess(calm, 0.001)

    def test_stop_triggers_beyond_sigma_multiple(self):
        state = self._state_with_position()
        # sigma 1% -> limite 8%; queda de 20% dispara
        trades = portfolio.check_stops(state, {"AAA": 80.0}, {"AAA": 0.01},
                                       "2026-02-10", 0.0)
        self.assertEqual(len(trades), 1)
        self.assertNotIn("AAA", state["positions"])
        self.assertIn("stop", trades[0]["reason"])
        self.assertIn("AAA", state["cooldown"])

    def test_stop_is_proportional_not_fixed(self):
        # mesma queda de 12%: ativo volatil aguenta, ativo estavel nao
        volatile = self._state_with_position()
        portfolio.check_stops(volatile, {"AAA": 88.0}, {"AAA": 0.03},
                              "2026-02-10", 0.0)
        self.assertIn("AAA", volatile["positions"])

        stable = self._state_with_position()
        portfolio.check_stops(stable, {"AAA": 88.0}, {"AAA": 0.005},
                              "2026-02-10", 0.0)
        self.assertNotIn("AAA", stable["positions"])

    def test_cooldown_blocks_then_expires(self):
        state = self._state_with_position()
        portfolio.check_stops(state, {"AAA": 50.0}, {"AAA": 0.01},
                              "2026-02-10", 0.0)
        self.assertIn("AAA", portfolio.active_cooldowns(state, "2026-02-20"))
        self.assertNotIn("AAA", portfolio.active_cooldowns(state, "2026-05-01"))

    def test_high_water_tracks_peak_not_last_price(self):
        state = self._state_with_position()
        portfolio.update_high_water(state, {"AAA": 130.0})
        portfolio.update_high_water(state, {"AAA": 110.0})
        self.assertEqual(state["positions"]["AAA"]["high_water"], 130.0)


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

    def test_slippage_costs_money(self):
        state = portfolio.new_state("equities", "SPY", "2026-01-05", 500.0)
        prices = {"AAA": 100.0}
        orders = portfolio.build_orders(state, {"AAA": 1.0}, prices)
        portfolio.execute_orders(state, orders, "2026-01-05", 100.0)
        self.assertLess(portfolio.nav(state, prices), config.INITIAL_CAPITAL_USD)

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
        self.assertEqual(portfolio.load_state("x"),
                         json.loads(json.dumps(state)))

    def test_rebalance_trigger_gives_reason(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        self.assertIn("primeira execucao",
                      portfolio.needs_rebalance(state, {}, {}, 2, "risk_on"))
        state["last_rebalance"] = "2026-01-05"
        state["last_regime"] = "risk_on"
        self.assertIn("mudanca de regime",
                      portfolio.needs_rebalance(state, {}, {}, 2, "risk_off"))
        self.assertIsNone(portfolio.needs_rebalance(state, {}, {}, 2, "risk_on"))
        self.assertIn("semanal",
                      portfolio.needs_rebalance(state, {}, {}, 0, "risk_on"))

    def test_decision_log_is_capped_and_deduped(self):
        state = portfolio.new_state("x", "SPY", "2026-01-05", 500.0)
        for i in range(config.DECISION_LOG_MAX_ENTRIES + 25):
            portfolio.log_decision(state, {"date": f"day-{i:04d}"})
        self.assertEqual(len(state["decision_log"]),
                         config.DECISION_LOG_MAX_ENTRIES)
        portfolio.log_decision(state, {"date": "day-0144", "regime": "risk_off"})
        self.assertEqual(len(state["decision_log"]),
                         config.DECISION_LOG_MAX_ENTRIES)
        self.assertEqual(state["decision_log"][-1]["regime"], "risk_off")


class TestB3(unittest.TestCase):
    def test_cdi_factor_anchored_to_inception(self):
        from trading_agent import data_sources
        rates = [("2026-01-02", 0.05), ("2026-01-05", 0.05),
                 ("2026-01-06", 0.05), ("2026-01-07", 0.05)]
        factor = data_sources.cdi_factor_since(rates, "2026-01-05", "2026-01-07")
        self.assertAlmostEqual(factor, 1.0005 ** 2, places=10)
        self.assertEqual(data_sources.cdi_factor_since(rates, "2026-01-05",
                                                       "2026-01-05"), 1.0)

    def test_cash_accrues_cdi(self):
        state = portfolio.new_state("b3", "^BVSP", "2026-01-05", 130_000.0,
                                    currency="BRL", initial_capital=50_000.0)
        rates = [("2026-01-05", 0.05), ("2026-01-06", 0.05), ("2026-01-07", 0.05)]
        portfolio.accrue_cash_cdi(state, rates, "2026-01-07")
        self.assertAlmostEqual(state["cash"], 50_000.0 * 1.0005 ** 2, places=4)

    def test_b3_hurdle_is_the_higher_of_ibov_and_cdi(self):
        universe = {f"T{i}": as_series(trending_series(50, 0.0008, 300))
                    for i in range(10)}
        bench = trending_series(130_000, 0.0002, 300)
        # CDI da janela muito alto: passa a ser o obstaculo e barra todos
        decision = strategy.b3_decision(universe, bench, cdi_window_return=5.0)
        self.assertEqual(decision["hurdle"], "CDI")
        self.assertEqual(decision["weights"], {})
        # CDI baixo: o obstaculo volta a ser o Ibovespa e a carteira monta
        decision = strategy.b3_decision(universe, bench, cdi_window_return=0.01)
        self.assertEqual(decision["hurdle"], "IBOV")
        self.assertEqual(len(decision["weights"]), config.B3_TOP_N)


class TestStructured(unittest.TestCase):
    def test_bs_call_above_intrinsic_and_rises_with_vol(self):
        from trading_agent import structured
        low = structured.bs_call_price(100, 103, 30 / 365, 0.10, 0.15)
        high = structured.bs_call_price(100, 103, 30 / 365, 0.10, 0.40)
        self.assertGreater(high, low)
        self.assertGreater(low, 0.0)
        self.assertAlmostEqual(structured.bs_call_price(110, 100, 0.0, 0.10, 0.20),
                               10.0, places=6)

    def test_covered_call_cycle(self):
        from trading_agent import structured
        state = portfolio.new_state("b3_estruturadas", "^BVSP", "2026-01-05",
                                    130_000.0, currency="BRL",
                                    initial_capital=50_000.0)
        state["positions"]["BOVA11"] = {"qty": 500.0, "avg_cost": 100.0}
        state["cash"] = 0.0
        structured.sell_new_call(state, 100.0, 0.25, 0.10, "2026-01-05")
        self.assertGreater(state["cash"], 0.0)
        sc = state["short_call"]
        self.assertAlmostEqual(sc["strike"], 103.0, places=2)
        self.assertIsNone(structured.settle_expired_call(state, 110.0, "2026-01-20"))
        cash_before = state["cash"]
        self.assertIsNotNone(structured.settle_expired_call(state, 110.0,
                                                            sc["expiry"]))
        self.assertAlmostEqual(cash_before - state["cash"],
                               (110.0 - 103.0) * 500.0, places=2)
        self.assertIsNone(state["short_call"])


class TestGarch(unittest.TestCase):
    def _simulate_garch_closes(self, n=600, omega=4e-6, alpha=0.08, beta=0.88):
        import math, random
        random.seed(3)
        var = omega / (1 - alpha - beta)
        price, closes = 100.0, [100.0]
        for _ in range(n):
            r = math.sqrt(var) * random.gauss(0, 1)
            price *= math.exp(r)
            closes.append(price)
            var = omega + alpha * r * r + beta * var
        return closes

    def test_fit_recovers_persistence(self):
        from trading_agent import garch
        omega, alpha, beta = garch.fit_garch11(
            garch.log_returns(self._simulate_garch_closes()))
        self.assertGreater(alpha, 0.0)
        self.assertGreater(beta, 0.5)
        self.assertLess(alpha + beta, 0.999)
        self.assertGreater(alpha + beta, 0.85)

    def test_forecast_close_to_long_run_vol(self):
        import math
        from trading_agent import garch
        vol = garch.forecast_avg_vol(self._simulate_garch_closes(), 21)
        long_run = math.sqrt(4e-6 / (1 - 0.96) * 252)
        self.assertGreater(vol, long_run * 0.35)
        self.assertLess(vol, long_run * 2.5)

    def test_insufficient_history_raises(self):
        from trading_agent import garch
        with self.assertRaises(ValueError):
            garch.fit_garch11([0.001] * 50)


class TestReport(unittest.TestCase):
    def _result(self):
        state = portfolio.new_state("equities", "SPY", "2026-01-05", 500.0)
        state["positions"] = {"AAA": {"qty": 100.0, "avg_cost": 100.0}}
        state["cash"] = 40_000.0
        state["history"] = [{"date": "2026-01-05", "nav": 50_000.0,
                             "benchmark_nav": 50_000.0}]
        return {
            "state": state,
            "entry": state["history"][-1],
            "trades": [{"date": "2026-01-05", "symbol": "AAA", "side": "buy",
                        "qty": 100.0, "price": 100.0, "value": 10_000.0}],
            "regime": "risk_on",
            "targets": {"AAA": 0.2},
            "prices": {"AAA": 100.0},
            "log": {"rebalance_trigger": "cadencia semanal (segunda-feira)",
                    "hurdle": "SPY", "hurdle_score": 0.12, "eligible_count": 7,
                    "selected": [], "stops": [{"symbol": "BBB",
                                               "reason": "stop: queda 20%"}],
                    "cooldowns": {"BBB": "2026-02-04"},
                    "data_failures": ["CCC"],
                    "rejected": [{"symbol": "DDD",
                                  "reason": "nao bate o benchmark"}],
                    "note": ""},
        }

    def test_report_has_numbers_and_audit_trail(self):
        content = report.build_report("2026-01-05", {"equities": self._result()},
                                      {"crypto": "sem rede"})
        self.assertIn("Acoes EUA", content)
        self.assertIn("COMPRA", content)
        self.assertIn("Alfa vs SPY", content)
        self.assertIn("ERRO", content)
        # rasto de decisao da secao 8
        self.assertIn("Rasto de decisao", content)
        self.assertIn("cadencia semanal", content)
        self.assertIn("STOP BBB", content)
        self.assertIn("carencia", content)
        self.assertIn("nao bate o benchmark", content)
        self.assertIn("CCC", content)

    def test_b3_alpha_uses_the_higher_benchmark(self):
        result = self._result()
        state = result["state"]
        state["currency"] = "BRL"
        state["benchmark2"] = {"symbol": "CDI"}
        # carteira +10%, IBOV +2%, CDI +6% -> alfa deve ser medido vs CDI
        result["entry"] = {"date": "2026-06-01", "nav": 55_000.0,
                           "benchmark_nav": 51_000.0, "benchmark2_nav": 53_000.0}
        state["history"] = [result["entry"]]
        section = report._sleeve_section("B3", "IBOV", result, "CDI")
        self.assertIn("Alfa vs o maior (CDI)", section)
        self.assertIn("+4.00%", section)


if __name__ == "__main__":
    unittest.main()


class TestCharts(unittest.TestCase):
    def _state(self, points, with_cdi=False):
        history = []
        for i, (nav, bench) in enumerate(points):
            entry = {"date": f"2026-08-{6 + i:02d}", "nav": nav,
                     "benchmark_nav": bench}
            if with_cdi:
                entry["benchmark2_nav"] = 50_000.0 * (1 + 0.0002 * i)
            history.append(entry)
        return {"initial_capital": 50_000.0, "currency": "USD",
                "history": history}

    def test_series_indexed_to_base_100(self):
        from trading_agent import charts
        state = self._state([(50_000.0, 50_000.0), (55_000.0, 52_500.0)])
        series = charts._series_for(state, "SPY", None)
        self.assertEqual([s["name"] for s in series], ["Carteira", "SPY"])
        self.assertAlmostEqual(series[0]["values"][0], 100.0, places=6)
        self.assertAlmostEqual(series[0]["values"][1], 110.0, places=6)
        self.assertAlmostEqual(series[1]["values"][1], 105.0, places=6)

    def test_second_benchmark_only_when_present(self):
        from trading_agent import charts
        plain = charts._series_for(self._state([(50_000.0, 50_000.0)]),
                                   "IBOV", "CDI")
        self.assertEqual(len(plain), 2)
        withcdi = charts._series_for(
            self._state([(50_000.0, 50_000.0)], with_cdi=True), "IBOV", "CDI")
        self.assertEqual([s["name"] for s in withcdi],
                         ["Carteira", "IBOV", "CDI"])

    def test_svg_is_self_contained_and_theme_aware(self):
        from trading_agent import charts
        svg = charts.build_svg("2026-08-07", [
            ("Acoes EUA vs SPY", self._state([(50_000.0, 50_000.0),
                                              (49_800.0, 50_200.0)]),
             "SPY", None)])
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("prefers-color-scheme: dark", svg)
        self.assertNotIn("http://", svg.replace('xmlns="http://www.w3.org/2000/svg"', ""))
        # identidade nunca so pela cor: rotulo direto de cada serie
        self.assertIn(">Carteira<", svg)
        self.assertIn(">SPY<", svg)
        # tooltip nativo por ponto
        self.assertIn("<title>", svg)

    def test_empty_history_does_not_crash(self):
        from trading_agent import charts
        svg = charts.build_svg("2026-08-07", [
            ("Vazia", {"initial_capital": 50_000.0, "history": []}, "SPY", None)])
        self.assertIn("sem historico ainda", svg)

    def test_converging_labels_are_pushed_apart(self):
        import re
        from trading_agent import charts
        # carteira e benchmark praticamente sobrepostos no fim
        state = self._state([(50_000.0, 50_000.0), (50_010.0, 50_005.0)])
        svg = charts.build_svg("2026-08-07", [("P", state, "SPY", None)])
        ys = [float(m) for m in re.findall(r'class="direct"[^>]*y="([\d.]+)"', svg)]
        self.assertEqual(len(ys), 2)
        self.assertGreaterEqual(abs(ys[0] - ys[1]), charts.MIN_LABEL_GAP - 0.01)

    def test_report_links_dated_chart(self):
        content = report.build_report("2026-08-07", {}, {})
        self.assertIn("2026-08-07-grafico.svg", content)


class TestCdiResilience(unittest.TestCase):
    """Uma indisponibilidade do Banco Central nao pode custar um dia inteiro
    as duas carteiras B3 — mas tambem nao pode inventar taxa nenhuma."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = Path(self.tmp.name) / "cdi_cache.json"
        patcher = mock.patch.object(data_sources, "_cdi_cache_path",
                                    lambda: self.cache)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_successful_fetch_populates_cache(self):
        payload = json.dumps([{"data": "05/01/2026", "valor": "0.05"}] * 12
                             ).encode()
        with mock.patch.object(self.ds, "_http_get", return_value=payload):
            rows = self.ds.fetch_bcb_cdi_daily()
        self.assertEqual(len(rows), 12)
        self.assertTrue(self.cache.exists())

    def test_outage_falls_back_to_cache(self):
        payload = json.dumps([{"data": "05/01/2026", "valor": "0.05"},
                              {"data": "06/01/2026", "valor": "0.05"}] * 6
                             ).encode()
        with mock.patch.object(self.ds, "_http_get", return_value=payload):
            fresh = self.ds.fetch_bcb_cdi_daily()
        with mock.patch.object(self.ds, "_http_get",
                               side_effect=self.ds.DataSourceError("502")):
            cached = self.ds.fetch_bcb_cdi_daily()
        self.assertEqual(cached, fresh)

    def test_outage_without_cache_still_fails_closed(self):
        with mock.patch.object(self.ds, "_http_get",
                               side_effect=self.ds.DataSourceError("502")):
            with self.assertRaises(self.ds.DataSourceError):
                self.ds.fetch_bcb_cdi_daily()

    def test_cache_does_not_invent_future_days(self):
        # a caixa so acumula ate ao ultimo dia realmente publicado
        state = portfolio.new_state("b3", "^BVSP", "2026-01-05", 130_000.0,
                                    currency="BRL", initial_capital=50_000.0)
        cached = [("2026-01-06", 0.05), ("2026-01-07", 0.05)]
        portfolio.accrue_cash_cdi(state, cached, "2026-01-20")
        self.assertAlmostEqual(state["cash"], 50_000.0 * 1.0005 ** 2, places=4)
        self.assertEqual(state["last_accrual_date"], "2026-01-07")


class TestPermanentHttpErrors(unittest.TestCase):
    def test_definitive_4xx_is_not_retried(self):
        import urllib.error
        from trading_agent import data_sources
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", None, None)

        with mock.patch.object(data_sources.urllib.request, "urlopen",
                               fake_urlopen), \
             mock.patch.object(data_sources.time, "sleep"):
            with self.assertRaises(data_sources.DataSourceError):
                data_sources._http_get("https://example.invalid/x")
        self.assertEqual(len(calls), 1)

    def test_transient_5xx_is_retried(self):
        import urllib.error
        from trading_agent import data_sources
        calls = []

        def fake_urlopen(req, timeout=None):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, 502, "Bad Gateway", None, None)

        with mock.patch.object(data_sources.urllib.request, "urlopen",
                               fake_urlopen), \
             mock.patch.object(data_sources.time, "sleep"):
            with self.assertRaises(data_sources.DataSourceError):
                data_sources._http_get("https://example.invalid/x")
        self.assertEqual(len(calls), data_sources.RETRIES)


class TestCdiHurdleGuard(unittest.TestCase):
    """Serie curta do CDI nao pode virar obstaculo baixo em silencio."""

    def test_short_series_means_no_cdi_hurdle(self):
        universe = {f"T{i}": as_series(trending_series(50, 0.0008, 300))
                    for i in range(10)}
        bench = trending_series(130_000, 0.0002, 300)
        # sem janela completa o chamador passa None -> obstaculo volta ao IBOV
        decision = strategy.b3_decision(universe, bench, cdi_window_return=None)
        self.assertEqual(decision["hurdle"], "IBOV")

    def test_engine_skips_cdi_hurdle_when_series_is_short(self):
        import inspect
        from trading_agent import engine
        src = inspect.getsource(engine.run_b3)
        # a guarda tem de existir: sem ela o acumulado de poucos dias passaria
        self.assertIn("if len(cdi_rates) >= window", src)


class TestBcbFallbackChain(unittest.TestCase):
    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(
            data_sources, "_cdi_cache_path",
            lambda: Path(self.tmp.name) / "cdi_cache.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_falls_through_to_a_working_endpoint(self):
        good = json.dumps([{"data": f"{d:02d}/01/2026", "valor": "0.05"}
                           for d in range(1, 15)]).encode()
        calls = []

        def flaky(url, timeout=30.0):
            calls.append(url)
            if "dataInicial" in url:
                raise self.ds.DataSourceError("502")
            return good

        with mock.patch.object(self.ds, "_http_get", flaky):
            rows = self.ds.fetch_bcb_cdi_daily()
        self.assertEqual(len(rows), 14)
        self.assertGreaterEqual(len(calls), 2)  # tentou o intervalo, depois ultimos/N

    def test_all_endpoints_down_and_no_cache_fails_closed(self):
        with mock.patch.object(self.ds, "_http_get",
                               side_effect=self.ds.DataSourceError("502")):
            with self.assertRaises(self.ds.DataSourceError):
                self.ds.fetch_bcb_cdi_daily()


class TestRateLimitBackoff(unittest.TestCase):
    """429 e a fonte a pedir para abrandar — repetir depressa so confirma o
    bloqueio e custa a carteira que corre a seguir."""

    def _run_with(self, code, headers=None):
        import urllib.error
        from trading_agent import data_sources
        waits, calls = [], []

        def fake_urlopen(req, timeout=None):
            calls.append(1)
            raise urllib.error.HTTPError(req.full_url, code, "x",
                                         headers or {}, None)

        with mock.patch.object(data_sources.urllib.request, "urlopen",
                               fake_urlopen), \
             mock.patch.object(data_sources.time, "sleep", waits.append):
            with self.assertRaises(data_sources.DataSourceError):
                data_sources._http_get("https://example.invalid/x")
        return waits, calls

    def test_429_waits_much_longer_than_a_generic_error(self):
        from trading_agent import data_sources
        rate_waits, _ = self._run_with(429)
        generic_waits, _ = self._run_with(503)
        self.assertGreaterEqual(min(rate_waits), data_sources.RATE_LIMIT_SLEEP_S[0])
        self.assertGreater(sum(rate_waits), sum(generic_waits) * 3)

    def test_429_honours_retry_after_header(self):
        waits, _ = self._run_with(429, headers={"Retry-After": "75"})
        self.assertIn(75.0, waits)

    def test_retry_after_is_capped(self):
        from trading_agent import data_sources
        waits, _ = self._run_with(429, headers={"Retry-After": "99999"})
        self.assertLessEqual(max(waits), data_sources.MAX_RETRY_AFTER_S)

    def test_garbage_retry_after_falls_back_to_default(self):
        from trading_agent import data_sources
        waits, _ = self._run_with(429, headers={"Retry-After": "amanha"})
        self.assertIn(data_sources.RATE_LIMIT_SLEEP_S[0], waits)
