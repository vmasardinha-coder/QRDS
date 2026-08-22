"""Testes offline do agente de trading (sem rede, dados sinteticos).

Cobrem as regras da Carta de Operacao: teto por posicao, piso de
diversificacao, forca relativa ao benchmark, filtro de liquidez, stop
estatistico com carencia, integridade de dado e log auditavel.
"""

from __future__ import annotations

import json
import tempfile
import urllib.error
import unittest
from pathlib import Path
from unittest import mock

from trading_agent import (config, cotahist, data_sources, portfolio, report,
                           strategy)

_CACHE_ISOLADO = None


def setUpModule():
    """Nenhum teste escreve no estado real do agente.

    'fetch_b3_daily' passou a gravar a serie do indice em disco, e os testes
    que substituem as fontes devolvem valores inventados. Sem este desvio, um
    teste como 'test_the_index_never_asks_the_archive' gravava o seu stub em
    trading_agent/state/ e o ficheiro seguia para o repositorio — aconteceu a
    2026-08-17, com um fecho de 130000.0 numa data de pregao real.
    """
    global _CACHE_ISOLADO
    _CACHE_ISOLADO = tempfile.TemporaryDirectory()
    destino = Path(_CACHE_ISOLADO.name) / "indice_cache.json"
    mock.patch.object(data_sources, "_index_cache_path",
                      lambda: destino).start()


def tearDownModule():
    mock.patch.stopall()
    if _CACHE_ISOLADO is not None:
        _CACHE_ISOLADO.cleanup()


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


class TestBenchmarkPriority(unittest.TestCase):
    """Perder o benchmark derruba a carteira toda; perder um ativo custa um
    nome. O orcamento de tentativas tem de refletir essa assimetria."""

    def setUp(self):
        from trading_agent import data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_benchmark_gets_more_attempts_than_a_constituent(self):
        import urllib.error
        from trading_agent import data_sources
        counts = []

        def make_counter():
            calls = []

            def fake(req, timeout=None):
                calls.append(1)
                raise urllib.error.HTTPError(req.full_url, 503, "x", {}, None)
            return calls, fake

        hosts = len(data_sources.YAHOO_HOSTS)
        for retries in (None, data_sources.BENCHMARK_RETRIES):
            calls, fake = make_counter()
            with mock.patch.object(data_sources.urllib.request, "urlopen", fake), \
                 mock.patch.object(data_sources.time, "sleep"):
                with self.assertRaises(data_sources.DataSourceError):
                    data_sources.fetch_yahoo_daily("^BVSP", retries=retries)
            counts.append(len(calls))
        # cada host recebe o orcamento completo de tentativas
        self.assertEqual(counts[0], data_sources.RETRIES * hosts)
        self.assertEqual(counts[1], data_sources.BENCHMARK_RETRIES * hosts)
        self.assertGreater(counts[1], counts[0])


class TestSourceRouting(unittest.TestCase):
    """Distinguir 'a fonte caiu' de 'este ativo nao existe la' e o que evita
    mandar 100 acoes para o Yahoo por causa de 3 tickers desconhecidos."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_missing_ticker_does_not_trip_the_breaker(self):
        with mock.patch.object(self.ds, "fetch_nasdaq_daily",
                               side_effect=self.ds.DataSourceError("indisponivel")), \
             mock.patch.object(self.ds, "fetch_stooq_daily",
                               side_effect=self.ds.DataSourceError("nao tem serie")), \
             mock.patch.object(self.ds, "fetch_yahoo_daily",
                               return_value=[("2026-01-01", 1.0, 1.0)] * 12), \
             mock.patch.object(self.ds.time, "sleep"):
            for _ in range(5):
                self.ds.fetch_equity_daily("XYZ")
        self.assertEqual(self.ds._STOOQ_CONSECUTIVE_FAILURES, 0)

    def test_source_outage_trips_the_breaker(self):
        with mock.patch.object(self.ds, "fetch_nasdaq_daily",
                               side_effect=self.ds.DataSourceError("indisponivel")), \
             mock.patch.object(self.ds, "fetch_stooq_daily",
                               side_effect=self.ds.SourceUnavailable("bloqueado")), \
             mock.patch.object(self.ds, "fetch_yahoo_daily",
                               return_value=[("2026-01-01", 1.0, 1.0)] * 12), \
             mock.patch.object(self.ds.time, "sleep"):
            for _ in range(4):
                self.ds.fetch_equity_daily("AAPL")
        self.assertGreaterEqual(self.ds._STOOQ_CONSECUTIVE_FAILURES,
                                self.ds._STOOQ_TRIP_AFTER)

    def test_crypto_falls_through_coinbase_to_binance(self):
        series = [("2026-01-01", 100.0, 5.0)] * 12
        with mock.patch.object(self.ds, "fetch_coinbase_daily",
                               side_effect=self.ds.DataSourceError("404")), \
             mock.patch.object(self.ds, "fetch_binance_daily", return_value=series):
            out = self.ds.fetch_crypto_daily("SUI", "sui")
        self.assertEqual(out, series)
        self.assertEqual(self.ds.SOURCE_TALLY.get("binance"), 1)

    def test_crypto_reports_when_every_source_fails(self):
        err = self.ds.DataSourceError("x")
        with mock.patch.object(self.ds, "fetch_coinbase_daily", side_effect=err), \
             mock.patch.object(self.ds, "fetch_binance_daily", side_effect=err), \
             mock.patch.object(self.ds, "fetch_coingecko_daily", side_effect=err):
            with self.assertRaises(self.ds.DataSourceError):
                self.ds.fetch_crypto_daily("NADA", "nada")

    def test_binance_volume_is_base_units_for_the_liquidity_filter(self):
        payload = json.dumps([[1767225600000, "1", "1", "1", "100.0", "7.5",
                               0, "0", 0, "0", "0", "0"]] * 12).encode()
        with mock.patch.object(self.ds, "_http_get", return_value=payload):
            rows = self.ds.fetch_binance_daily("BTC")
        self.assertEqual(rows[0][1], 100.0)   # fecho
        self.assertEqual(rows[0][2], 7.5)     # volume na moeda base
        # preco x volume = giro em USD, comparavel ao da Coinbase
        self.assertEqual(rows[0][1] * rows[0][2], 750.0)


class TestBrapiSource(unittest.TestCase):
    """A B3 passa a ter uma fonte independente do Yahoo, que nos bloqueou."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def _payload(self, n=12):
        return json.dumps({"results": [{"historicalDataPrice": [
            {"date": 1767225600 + i * 86400, "close": 30.0 + i, "volume": 5_000_000}
            for i in range(n)]}]}).encode()

    def test_parses_history_into_series(self):
        with mock.patch.object(self.ds, "_http_get", return_value=self._payload()):
            rows = self.ds.fetch_brapi_daily("PETR4")
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0][1], 30.0)
        self.assertEqual(rows[0][2], 5_000_000)
        self.assertEqual(rows, sorted(rows))

    def test_short_history_is_rejected_not_padded(self):
        with mock.patch.object(self.ds, "_http_get",
                               return_value=self._payload(n=3)):
            with self.assertRaises(self.ds.DataSourceError):
                self.ds.fetch_brapi_daily("PETR4")

    def test_b3_prefers_brapi_and_falls_back_to_yahoo(self):
        series = [("2026-01-01", 30.0, 5e6)] * 12
        with mock.patch.object(self.ds, "fetch_brapi_daily", return_value=series), \
             mock.patch.object(self.ds.time, "sleep"):
            self.ds.fetch_b3_daily("PETR4")
        self.assertEqual(self.ds.SOURCE_TALLY.get("brapi"), 1)

        self.ds.SOURCE_TALLY.clear()
        with mock.patch.object(self.ds, "fetch_brapi_daily",
                               side_effect=self.ds.DataSourceError("x")), \
             mock.patch.object(self.ds, "fetch_yahoo_daily", return_value=series), \
             mock.patch.object(self.ds.time, "sleep"):
            self.ds.fetch_b3_daily("PETR4")
        self.assertEqual(self.ds.SOURCE_TALLY.get("yahoo"), 1)

    def test_both_sources_down_names_both_in_the_error(self):
        err = self.ds.DataSourceError("indisponivel")
        with mock.patch.object(self.ds, "fetch_brapi_daily", side_effect=err), \
             mock.patch.object(self.ds, "fetch_yahoo_daily", side_effect=err):
            with self.assertRaises(self.ds.DataSourceError) as ctx:
                self.ds.fetch_b3_daily("PETR4")
        self.assertIn("brapi", str(ctx.exception))
        self.assertIn("yahoo", str(ctx.exception))

    def test_yahoo_tries_the_second_host_when_the_first_is_blocked(self):
        import urllib.error
        seen = []

        def fake(url, timeout=30.0, retries=None):
            seen.append(url)
            if "query1" in url:
                raise self.ds.DataSourceError("429")
            return json.dumps({"chart": {"result": [{
                "timestamp": [1767225600 + i * 86400 for i in range(12)],
                "indicators": {"quote": [{"close": [10.0] * 12,
                                          "volume": [1000] * 12}]}}]}}).encode()

        with mock.patch.object(self.ds, "_http_get", fake):
            rows = self.ds.fetch_yahoo_daily("SPY")
        self.assertEqual(len(rows), 12)
        self.assertTrue(any("query2" in u for u in seen))


class TestYahooBreaker(unittest.TestCase):
    """Sem disjuntor, 100 tickers x 2 hosts x esperas de 429 davam mais de oito
    horas — muito acima do limite de uma hora do ciclo."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_repeated_429_stops_further_requests(self):
        import urllib.error
        calls = []

        def fake(req, timeout=None):
            calls.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 429, "x", {}, None)

        with mock.patch.object(self.ds.urllib.request, "urlopen", fake), \
             mock.patch.object(self.ds.time, "sleep"):
            for _ in range(20):
                with self.assertRaises(self.ds.DataSourceError):
                    self.ds.fetch_yahoo_daily("AAPL")
        # depois de disparar, os pedidos seguintes nem saem
        self.assertLess(len(calls), self.ds.RETRIES * len(self.ds.YAHOO_HOSTS) * 3)
        self.assertTrue(self.ds._YAHOO_RATE_LIMITED)

    def test_breaker_resets_between_cycles(self):
        self.ds._YAHOO_RATE_LIMITED = True
        self.ds.reset_source_breakers()
        self.assertFalse(self.ds._YAHOO_RATE_LIMITED)

    def test_b3_still_serves_from_brapi_when_yahoo_is_tripped(self):
        self.ds._YAHOO_RATE_LIMITED = True
        series = [("2026-01-01", 30.0, 5e6)] * 12
        with mock.patch.object(self.ds, "fetch_brapi_daily", return_value=series), \
             mock.patch.object(self.ds.time, "sleep"):
            out = self.ds.fetch_b3_daily("PETR4")
        self.assertEqual(out, series)


class TestBrapiRanges(unittest.TestCase):
    """O plano livre da brapi limita o historico; pedir do mais longo para o
    mais curto e ficar com o melhor evita perder a carteira por isso."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def _payload(self, n):
        return json.dumps({"results": [{"historicalDataPrice": [
            {"date": 1767225600 + i * 86400, "close": 30.0, "volume": 1e6}
            for i in range(n)]}]}).encode()

    def test_falls_back_to_a_shorter_range_when_the_long_one_fails(self):
        seen = []

        def fake(url, timeout=30.0, retries=None, headers=None):
            seen.append(url)
            if "range=2y" in url or "range=1y" in url:
                raise self.ds.DataSourceError("HTTP 401 (definitivo)")
            return self._payload(60)

        with mock.patch.object(self.ds, "_http_get", fake):
            rows = self.ds.fetch_brapi_daily("PETR4")
        self.assertEqual(len(rows), 60)
        self.assertTrue(any("range=6mo" in u for u in seen))

    def test_stops_early_once_the_history_is_long_enough(self):
        seen = []

        def fake(url, timeout=30.0, retries=None, headers=None):
            seen.append(url)
            return self._payload(300)

        with mock.patch.object(self.ds, "_http_get", fake):
            rows = self.ds.fetch_brapi_daily("PETR4")
        self.assertEqual(len(rows), 300)
        self.assertEqual(len(seen), 1)   # nao insiste depois de ter o que precisa

    def test_error_names_the_ranges_it_tried(self):
        with mock.patch.object(self.ds, "_http_get",
                               side_effect=self.ds.DataSourceError("HTTP 401")):
            with self.assertRaises(self.ds.DataSourceError) as ctx:
                self.ds.fetch_brapi_daily("PETR4")
        self.assertIn("2y", str(ctx.exception))


class TestFailureTelemetry(unittest.TestCase):
    """Uma fonte que nunca serviu tem de ser distinguivel de uma que nem foi
    consultada — foi essa ambiguidade que me fez adivinhar durante dias."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_records_source_and_reason(self):
        with mock.patch.object(self.ds, "fetch_brapi_daily",
                               side_effect=self.ds.SourceUnavailable("HTTP 401 (definitivo)")), \
             mock.patch.object(self.ds, "fetch_yahoo_daily",
                               side_effect=self.ds.RateLimited("429")):
            with self.assertRaises(self.ds.DataSourceError):
                self.ds.fetch_b3_daily("^BVSP")
        self.assertEqual(self.ds.FAILURE_TALLY["brapi"]["n"], 1)
        self.assertIn("401", self.ds.FAILURE_TALLY["brapi"]["motivo"])
        self.assertIn("429", self.ds.FAILURE_TALLY["yahoo"]["motivo"])

    def test_counts_accumulate_across_tickers(self):
        with mock.patch.object(self.ds, "fetch_brapi_daily",
                               side_effect=self.ds.SourceUnavailable("HTTP 401")), \
             mock.patch.object(self.ds, "fetch_yahoo_daily",
                               side_effect=self.ds.DataSourceError("x")):
            for _ in range(3):
                with self.assertRaises(self.ds.DataSourceError):
                    self.ds.fetch_b3_daily("PETR4")
        self.assertEqual(self.ds.FAILURE_TALLY["brapi"]["n"], 3)

    def test_stooq_tries_the_mirror_host(self):
        seen = []

        def fake(url, timeout=30.0, retries=None):
            seen.append(url)
            if "stooq.com" in url:
                raise self.ds.DataSourceError("timeout")
            return b"Date,Open,High,Low,Close,Volume\n" + b"\n".join(
                f"2026-01-{d:02d},1,1,1,10.0,1000".encode() for d in range(1, 15))

        with mock.patch.object(self.ds, "_http_get", fake):
            rows = self.ds.fetch_stooq_daily("SPY")
        self.assertEqual(len(rows), 14)
        self.assertTrue(any("stooq.pl" in u for u in seen))

    def test_error_section_surfaces_source_failures(self):
        section = report._error_section(
            "Acoes B3", "sem fonte",
            {"brapi": {"n": 51, "motivo": "HTTP 401 (definitivo)"},
             "yahoo": {"n": 2, "motivo": "429"}})
        self.assertIn("brapi falhou 51x", section)
        self.assertIn("401", section)
        self.assertIn("yahoo falhou 2x", section)


class TestStooqClassification(unittest.TestCase):
    """Corpo vazio da Stooq e bloqueio (falha da fonte); corpo com conteudo
    reconhecivel e papel inexistente. Confundir os dois foi o que mandou as
    100 acoes para o Yahoo."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_empty_body_is_a_source_outage(self):
        with mock.patch.object(self.ds, "_http_get", return_value=b"\n"):
            with self.assertRaises(self.ds.SourceUnavailable):
                self.ds.fetch_stooq_daily("SPY")

    def test_long_body_without_rows_is_a_missing_ticker(self):
        body = b"Date,Open,High,Low,Close,Volume\n" + b"# " + b"x" * 250
        with mock.patch.object(self.ds, "_http_get", return_value=body):
            with self.assertRaises(self.ds.DataSourceError) as ctx:
                self.ds.fetch_stooq_daily("NOPE")
        self.assertNotIsInstance(ctx.exception, self.ds.SourceUnavailable)

    def test_error_carries_the_body_for_diagnosis(self):
        with mock.patch.object(self.ds, "_http_get", return_value=b"No data"):
            with self.assertRaises(self.ds.DataSourceError) as ctx:
                self.ds.fetch_stooq_daily("SPY")
        self.assertIn("No data", str(ctx.exception))


class TestStooqHtmlBlock(unittest.TestCase):
    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_html_response_is_a_block_not_a_missing_ticker(self):
        html = (b'<!DOCTYPE html><html><head><meta charset="utf-8">'
                b'<meta name="robots" content="noindex,nofollow"></head>'
                b'<body><noscript>Turn on JavaScript</noscript></body></html>')
        with mock.patch.object(self.ds, "_http_get", return_value=html):
            with self.assertRaises(self.ds.SourceUnavailable):
                self.ds.fetch_stooq_daily("SPY")

    def test_a_block_trips_the_breaker_so_we_stop_asking(self):
        html = b"<html><noscript>x</noscript></html>"
        with mock.patch.object(self.ds, "fetch_nasdaq_daily",
                               side_effect=self.ds.DataSourceError("indisponivel")), \
             mock.patch.object(self.ds, "_http_get", return_value=html), \
             mock.patch.object(self.ds, "fetch_yahoo_daily",
                               return_value=[("2026-01-01", 1.0, 1.0)] * 12), \
             mock.patch.object(self.ds.time, "sleep"):
            for _ in range(self.ds._STOOQ_TRIP_AFTER):
                self.ds.fetch_equity_daily("AAPL")
        self.assertGreaterEqual(self.ds._STOOQ_CONSECUTIVE_FAILURES,
                                self.ds._STOOQ_TRIP_AFTER)


class TestNasdaqSource(unittest.TestCase):
    """Fonte escolhida por medicao no runner: 549 pregoes, SPY pela classe
    'etf', e doze pedidos seguidos sem limite de taxa."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def _payload(self, n=12, close="$308.26", volume="44,812,500"):
        rows = [{"date": f"08/{1 + i % 28:02d}/2026", "close": close,
                 "volume": volume, "open": close, "high": close, "low": close}
                for i in range(n)]
        return json.dumps({"data": {"tradesTable": {"rows": rows}}}).encode()

    def test_parses_currency_and_thousands_separators(self):
        with mock.patch.object(self.ds, "_http_get", return_value=self._payload()):
            rows = self.ds.fetch_nasdaq_daily("AAPL")
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0][1], 308.26)
        self.assertEqual(rows[0][2], 44_812_500.0)
        self.assertEqual(rows, sorted(rows))          # ordem ascendente
        self.assertRegex(rows[0][0], r"^\d{4}-\d{2}-\d{2}$")

    def test_etfs_are_asked_as_etf_first(self):
        seen = []

        def fake(url, timeout=30.0, retries=None):
            seen.append(url)
            return self._payload()

        with mock.patch.object(self.ds, "_http_get", fake):
            self.ds.fetch_nasdaq_daily("SPY")
        self.assertIn("assetclass=etf", seen[0])

    def test_stocks_fall_back_to_the_etf_class(self):
        seen = []

        def fake(url, timeout=30.0, retries=None):
            seen.append(url)
            if "assetclass=stocks" in url:
                return json.dumps({"data": {"tradesTable": {"rows": []}}}).encode()
            return self._payload()

        with mock.patch.object(self.ds, "_http_get", fake):
            rows = self.ds.fetch_nasdaq_daily("QQQ")
        self.assertEqual(len(rows), 12)
        self.assertIn("assetclass=stocks", seen[0])
        self.assertIn("assetclass=etf", seen[1])

    def test_unparsable_rows_are_dropped_not_guessed(self):
        rows = [{"date": "08/01/2026", "close": "N/A", "volume": "--"},
                {"date": "nao-e-data", "close": "$10.00", "volume": "1,000"}]
        rows += [{"date": f"08/{2 + i:02d}/2026", "close": "$10.00",
                  "volume": "1,000"} for i in range(12)]
        payload = json.dumps({"data": {"tradesTable": {"rows": rows}}}).encode()
        with mock.patch.object(self.ds, "_http_get", return_value=payload):
            out = self.ds.fetch_nasdaq_daily("AAPL")
        self.assertEqual(len(out), 12)

    def test_equities_prefer_nasdaq(self):
        series = [("2026-01-01", 10.0, 1000.0)] * 12
        with mock.patch.object(self.ds, "fetch_nasdaq_daily", return_value=series), \
             mock.patch.object(self.ds.time, "sleep"):
            self.ds.fetch_equity_daily("AAPL")
        self.assertEqual(self.ds.SOURCE_TALLY.get("nasdaq"), 1)

    def test_nasdaq_failure_falls_through_to_the_old_sources(self):
        series = [("2026-01-01", 10.0, 1000.0)] * 12
        with mock.patch.object(self.ds, "fetch_nasdaq_daily",
                               side_effect=self.ds.SourceUnavailable("502")), \
             mock.patch.object(self.ds, "fetch_stooq_daily",
                               side_effect=self.ds.SourceUnavailable("html")), \
             mock.patch.object(self.ds, "fetch_yahoo_daily", return_value=series), \
             mock.patch.object(self.ds.time, "sleep"):
            out = self.ds.fetch_equity_daily("AAPL")
        self.assertEqual(out, series)
        self.assertEqual(self.ds.FAILURE_TALLY["nasdaq"]["n"], 1)


class TestSecretRedaction(unittest.TestCase):
    """As mensagens de falha sao publicadas no relatorio, que vive num
    repositorio publico. Uma credencial numa URL de erro acaba la — foi o que
    aconteceu com o token da brapi no ciclo de 12/08."""

    def setUp(self):
        from trading_agent import data_sources
        self.ds = data_sources
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_redact_hides_every_secret_parameter(self):
        for name in self.ds.SECRET_PARAMS:
            url = f"https://x.dev/api?range=2y&{name}=SEGREDO123&z=1"
            out = self.ds.redact(url)
            self.assertNotIn("SEGREDO123", out)
            self.assertIn("range=2y", out)   # o resto continua legivel
            self.assertIn("z=1", out)

    def test_redact_is_case_insensitive(self):
        self.assertNotIn("ABC", self.ds.redact("https://x.dev/a?TOKEN=ABC"))

    def test_http_errors_never_carry_the_secret(self):
        import urllib.error

        def fake(req, timeout=None):
            raise urllib.error.HTTPError(req.full_url, 400, "Bad", {}, None)

        with mock.patch.object(self.ds.urllib.request, "urlopen", fake), \
             mock.patch.object(self.ds.time, "sleep"):
            with self.assertRaises(self.ds.DataSourceError) as ctx:
                self.ds._http_get("https://brapi.dev/api/quote/PETR4?token=SEGREDO123")
        self.assertNotIn("SEGREDO123", str(ctx.exception))

    def test_brapi_sends_the_token_as_a_header_not_in_the_url(self):
        seen = {}

        def fake(url, timeout=30.0, retries=None, headers=None):
            seen["url"] = url
            seen["headers"] = headers or {}
            return json.dumps({"results": [{"historicalDataPrice": [
                {"date": 1767225600 + i * 86400, "close": 30.0, "volume": 1e6}
                for i in range(300)]}]}).encode()

        with mock.patch.dict("os.environ", {"BRAPI_TOKEN": "SEGREDO123"}), \
             mock.patch.object(self.ds, "_http_get", fake):
            self.ds.fetch_brapi_daily("PETR4")
        self.assertNotIn("SEGREDO123", seen["url"])
        self.assertNotIn("token=", seen["url"])
        self.assertEqual(seen["headers"].get("Authorization"), "Bearer SEGREDO123")

    def test_published_files_carry_no_token(self):
        from pathlib import Path
        import re
        leaked = []
        for path in list(Path("trading_agent/reports").rglob("*.md")) + \
                    list(Path("trading_agent/state").glob("*.json")):
            if re.search(r"token=(?!\*)[A-Za-z0-9]{4}", path.read_text(encoding="utf-8")):
                leaked.append(str(path))
        self.assertEqual(leaked, [])


class TestUniverseHygiene(unittest.TestCase):
    """Um ticker extinto encolhe o universo em silencio.

    A carteira nao fica errada — fica mais pequena do que o mandante decidiu,
    e o relatorio so mostra isso como uma linha de "sem dado" entre outras.
    """

    def test_no_duplicate_tickers(self):
        for nome, universo in (("B3", config.B3_UNIVERSE),
                               ("EUA", config.EQUITY_UNIVERSE)):
            with self.subTest(universo=nome):
                repetidos = {t for t in universo if universo.count(t) > 1}
                self.assertEqual(repetidos, set())

    def test_symbols_retired_by_corporate_action_are_gone(self):
        # Sucessoes confirmadas no arquivo da B3 (2026-08-15): o antigo para de
        # negociar e o novo comeca no pregao seguinte, com o nome da empresa ou
        # o emissor do ISIN a confirmar.
        for morto, vivo in (("CPLE6", "CPLE3"), ("BRFS3", "MBRF3"),
                            ("ELET3", "AXIA3"), ("EMBR3", "EMBJ3"),
                            ("NTCO3", "NATU3")):
            with self.subTest(ticker=morto):
                self.assertNotIn(morto, config.B3_UNIVERSE)
                self.assertIn(vivo, config.B3_UNIVERSE)

    def test_jbs_is_out_because_what_remains_on_b3_is_a_bdr(self):
        # A JBS passou a negociar em Nova Iorque; o que sobrou na B3 e JBSS32,
        # um BDR. Um recibo de acoes estrangeiras tem exposicao cambial e nao
        # e acao brasileira — nao entra numa carteira de acoes da B3 so para
        # manter a contagem de nomes.
        for ticker in ("JBSS3", "JBSS32"):
            self.assertNotIn(ticker, config.B3_UNIVERSE)


def _cotahist_record(date="20260813", codneg="PETR4", tpmerc="010",
                     preult="0000000004190", quatot="000000000012345678",
                     tipreg="01"):
    """Monta um registo COTAHIST de 245 caracteres por posicao fixa."""
    linha = (
        tipreg                      # 01-02  TIPREG
        + date                      # 03-10  DATA
        + "02"                      # 11-12  CODBDI
        + codneg.ljust(12)          # 13-24  CODNEG
        + tpmerc                    # 25-27  TPMERC
        + "PETROBRAS   "            # 28-39  NOMRES
        + "PN        "              # 40-49  ESPECI
        + "   "                     # 50-52  PRAZOT
        + "R$  "                    # 53-56  MODREF
        + "0000000004200"           # 57-69  PREABE
        + "0000000004250"           # 70-82  PREMAX
        + "0000000004150"           # 83-95  PREMIN
        + "0000000004200"           # 96-108 PREMED
        + preult                    # 109-121 PREULT
        + "0000000004190"           # 122-134 PREOFC
        + "0000000004200"           # 135-147 PREOFV
        + "01234"                   # 148-152 TOTNEG
        + quatot                    # 153-170 QUATOT
        + "000000000051750000"      # 171-188 VOLTOT
    )
    return linha.ljust(245)


def _cotahist_zip(linhas):
    import io
    import zipfile
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("COTAHIST_A2026.TXT",
                    "\r\n".join(linhas).encode("latin-1"))
    return buffer.getvalue()


class TestCotahistParsing(unittest.TestCase):
    """O arquivo da B3 e posicional: um desalinhamento de um caracter troca
    silenciosamente preco por volume, por isso o formato e testado a serio.
    """

    def test_reads_price_with_implied_decimals(self):
        blob = _cotahist_zip([_cotahist_record()])
        series = cotahist.parse(blob, {"PETR4"})
        self.assertEqual(series["PETR4"], [("2026-08-13", 41.90, 12345678.0)])

    def test_only_the_requested_tickers_come_back(self):
        blob = _cotahist_zip([_cotahist_record(codneg="PETR4"),
                              _cotahist_record(codneg="VALE3")])
        series = cotahist.parse(blob, {"PETR4"})
        self.assertEqual(sorted(series), ["PETR4"])

    def test_options_and_futures_are_excluded(self):
        # so mercado a vista (TPMERC 010): uma opcao sobre PETR4 tem o mesmo
        # prefixo mas nao e o ativo
        blob = _cotahist_zip([_cotahist_record(tpmerc="070"),
                              _cotahist_record(tpmerc="030")])
        self.assertEqual(cotahist.parse(blob, {"PETR4"}), {})

    def test_header_and_trailer_records_are_ignored(self):
        blob = _cotahist_zip([_cotahist_record(tipreg="00"),
                              _cotahist_record(tipreg="99")])
        self.assertEqual(cotahist.parse(blob, {"PETR4"}), {})

    def test_corrupt_row_is_skipped_not_guessed(self):
        bom = _cotahist_record(date="20260813")
        mau = _cotahist_record(date="20260812", preult="00000000041XX")
        series = cotahist.parse(_cotahist_zip([mau, bom]), {"PETR4"})
        self.assertEqual(series["PETR4"], [("2026-08-13", 41.90, 12345678.0)])

    def test_zero_price_is_dropped(self):
        blob = _cotahist_zip([_cotahist_record(preult="0000000000000")])
        self.assertEqual(cotahist.parse(blob, {"PETR4"}), {})

    def test_unreadable_zip_is_a_source_error(self):
        with self.assertRaises(cotahist.CotahistError):
            cotahist.parse(b"nao sou um zip", {"PETR4"})


class TestCotahistWiring(unittest.TestCase):

    def setUp(self):
        cotahist.reset()
        self.addCleanup(cotahist.reset)

    def test_series_for_without_priming_is_an_error_not_a_silent_empty(self):
        with self.assertRaises(cotahist.CotahistError):
            cotahist.series_for("PETR4")

    def test_priming_twice_does_not_download_twice(self):
        chamadas = []

        def falso_load(tickers, hoje=None):
            chamadas.append(tuple(tickers))
            return {"PETR4": [("2026-08-13", 41.9, 1.0)]}

        with mock.patch.object(cotahist, "load", falso_load):
            cotahist.prime(["PETR4"])
            cotahist.prime(["PETR4"])
        self.assertEqual(len(chamadas), 1)

    def test_a_missing_ticker_does_not_force_a_reload(self):
        # BOVA11 pedido mas ausente do arquivo: nao pode fazer o ciclo puxar
        # 150 MB outra vez a cada chamada
        chamadas = []

        def falso_load(tickers, hoje=None):
            chamadas.append(tuple(tickers))
            return {"PETR4": [("2026-08-13", 41.9, 1.0)]}

        with mock.patch.object(cotahist, "load", falso_load):
            cotahist.prime(["PETR4", "BOVA11"])
            cotahist.prime(["PETR4", "BOVA11"])
        self.assertEqual(len(chamadas), 1)

    def test_b3_cascade_tries_the_official_archive_first(self):
        ordem = []

        def falso_cotahist(ticker):
            ordem.append("cotahist")
            return [("2026-08-13", 41.9, 1.0)] * 300

        with mock.patch.object(data_sources, "fetch_cotahist_daily",
                               falso_cotahist):
            series = data_sources.fetch_b3_daily("PETR4")
        self.assertEqual(ordem, ["cotahist"])
        self.assertEqual(len(series), 300)

    def test_the_index_never_asks_the_archive(self):
        # COTAHIST nao tem indices; pedir ^BVSP la seria uma falha garantida
        ordem = []

        with mock.patch.object(data_sources, "fetch_cotahist_daily",
                               lambda t: ordem.append("cotahist")), \
             mock.patch.object(data_sources, "fetch_brapi_daily",
                               lambda t: [("2026-08-13", 130000.0, 0.0)]):
            data_sources.fetch_b3_daily("^BVSP", is_benchmark=True)
        self.assertEqual(ordem, [])

    def test_archive_failure_falls_through_to_brapi(self):
        def falha(ticker):
            raise data_sources.DataSourceError("COTAHIST fora do ar")

        with mock.patch.object(data_sources, "fetch_cotahist_daily", falha), \
             mock.patch.object(data_sources, "fetch_brapi_daily",
                               lambda t: [("2026-08-13", 41.9, 1.0)]):
            series = data_sources.fetch_b3_daily("PETR4")
        self.assertEqual(series, [("2026-08-13", 41.9, 1.0)])


class TestSourceFailureClassification(unittest.TestCase):
    """Uma fonte que nao lista um ativo nao esta avariada.

    Confundir as duas coisas fazia o relatorio anunciar "coinbase falhou 31x"
    enquanto a Binance servia essas 31 e nenhuma moeda ficava de fora — um
    alarme falso que faz perder a confianca nos alarmes verdadeiros.
    """

    def setUp(self):
        data_sources.reset_source_breakers()
        self.addCleanup(data_sources.reset_source_breakers)

    def test_missing_asset_is_not_counted_as_an_outage(self):
        data_sources._note_failure(
            "coinbase", data_sources.DataSourceError("HTTP 404 (definitivo)"))
        self.assertEqual(data_sources.FAILURE_TALLY, {})
        self.assertEqual(data_sources.MISSING_TALLY["coinbase"]["n"], 1)

    def test_a_blocked_source_is_still_an_outage(self):
        data_sources._note_failure(
            "yahoo", data_sources.RateLimited("429 apos 3 tentativas"))
        self.assertEqual(data_sources.MISSING_TALLY, {})
        self.assertEqual(data_sources.FAILURE_TALLY["yahoo"]["n"], 1)

    def test_the_archive_not_loading_is_an_outage_not_a_missing_ticker(self):
        cotahist.reset()
        self.addCleanup(cotahist.reset)
        with self.assertRaises(data_sources.SourceUnavailable):
            data_sources.fetch_cotahist_daily("PETR4")

    def test_a_ticker_absent_from_the_archive_is_not_an_outage(self):
        cotahist.reset()
        self.addCleanup(cotahist.reset)
        with mock.patch.object(cotahist, "load",
                               lambda t, hoje=None: {"PETR4": [("2026-08-13", 1.0, 1.0)]}):
            cotahist.prime(["PETR4", "NAOEXISTE3"])
        with self.assertRaises(data_sources.DataSourceError) as caught:
            data_sources.fetch_cotahist_daily("NAOEXISTE3")
        self.assertNotIsInstance(caught.exception, data_sources.SourceUnavailable)


class TestCotahistDownloadResilience(unittest.TestCase):
    """O ciclo de 2026-08-14 caiu com IncompleteRead nos 62 MB do ano corrente
    e mandou as 51 series para a brapi, que so tem historico truncado. Num dia
    de rebalanceio isso teria liquidado a carteira por causa da rede.
    """

    def test_a_cut_transfer_resumes_instead_of_starting_over(self):
        pedidos = []

        def falso_pedaco(url, desde, timeout):
            pedidos.append(desde)
            if desde == 0:
                return b"a" * 10, 25        # corta a meio
            return b"b" * 15, 25

        with mock.patch.object(cotahist, "_pedaco", falso_pedaco):
            dados = cotahist._download(2026)
        self.assertEqual(pedidos, [0, 10])   # retomou, nao recomecou
        self.assertEqual(len(dados), 25)

    def test_it_gives_up_with_a_reason_instead_of_looping_forever(self):
        with mock.patch.object(cotahist, "_pedaco",
                               lambda url, desde, timeout: (b"", None)), \
             mock.patch.object(cotahist.time, "sleep", lambda s: None):
            with self.assertRaises(cotahist.CotahistError) as caught:
                cotahist._download(2026)
        self.assertIn("vazia", str(caught.exception))

    def test_a_permanent_http_error_is_not_retried(self):
        tentativas = []

        def falha(url, desde, timeout):
            tentativas.append(desde)
            raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

        with mock.patch.object(cotahist, "_pedaco", falha), \
             mock.patch.object(cotahist.time, "sleep", lambda s: None):
            with self.assertRaises(cotahist.CotahistError):
                cotahist._download(2026)
        self.assertEqual(len(tentativas), 1)


class TestRefusedVersusMissing(unittest.TestCase):
    """A classificacao tem de nascer onde o codigo HTTP e conhecido.

    Antes vinha do tipo da excecao, e isso punha 401 ("a fonte recusa-te") no
    mesmo saco que 404 ("esse ativo nao existe").
    """

    def _get(self, code):
        def falso(req, timeout=None):
            raise urllib.error.HTTPError("https://x/y", code, "erro", None, None)
        with mock.patch.object(data_sources.urllib.request, "urlopen", falso):
            return data_sources._http_get("https://x/y", retries=1)

    def test_forbidden_is_a_source_refusing_us(self):
        for code in (401, 403):
            with self.subTest(code=code):
                with self.assertRaises(data_sources.SourceUnavailable):
                    self._get(code)

    def test_not_found_is_just_a_missing_asset(self):
        for code in (400, 404, 410, 422):
            with self.subTest(code=code):
                with self.assertRaises(data_sources.DataSourceError) as caught:
                    self._get(code)
                self.assertNotIsInstance(caught.exception,
                                         data_sources.SourceUnavailable)


class TestIndexHistoryCache(unittest.TestCase):
    """O cache do indice existe porque nenhuma fonte da o Ibovespa longo.

    Medido no runner a 2026-08-17: a brapi recusa range 2y/1y/6mo do ^BVSP com
    HTTP 400 e so serve 3mo (64 pregoes); a Stooq devolve pagina anti-robo nos
    dois hosts; o SGS nao tem a serie; o Yahoo estava em 429. A SMA 200 precisa
    de 200 pregoes, por isso a serie tem de ser acumulada ao longo dos ciclos.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        caminho = Path(self.tmp.name) / "indice_cache.json"
        p = mock.patch.object(data_sources, "_index_cache_path",
                              lambda: caminho)
        p.start()
        self.addCleanup(p.stop)

    def test_the_suite_never_writes_to_the_real_state_dir(self):
        # Guarda para o desvio de 'setUpModule' nao ser removido sem se dar por
        # isso: se voltar a apontar para trading_agent/state/, os stubs dos
        # testes voltam a ser commitados como se fossem cotacoes.
        real = Path(data_sources.__file__).resolve().parent / "state"
        self.assertNotIn(real, data_sources._index_cache_path().parents)

    def test_history_accumulates_across_cycles(self):
        # Dois ciclos com janelas curtas que se sobrepoem: o que fica guardado
        # e a uniao, que e maior que qualquer uma das fontes isolada.
        ciclo1 = [("2026-01-05", 100.0, 1.0), ("2026-01-06", 101.0, 1.0)]
        ciclo2 = [("2026-01-06", 101.0, 1.0), ("2026-01-07", 102.0, 1.0)]
        data_sources._absorb_index_history("^BVSP", ciclo1)
        junto = data_sources._absorb_index_history("^BVSP", ciclo2)
        self.assertEqual([d for d, _, _ in junto],
                         ["2026-01-05", "2026-01-06", "2026-01-07"])

    def test_cached_history_makes_the_regime_filter_evaluable(self):
        # O ponto da coisa: 64 pregoes nao chegam para a SMA 200, e ao fim de
        # ciclos suficientes chegam. Sem isto o filtro nunca corria.
        curto = [(f"2026-01-{d:02d}", 100.0, 1.0) for d in range(1, 29)]
        self.assertFalse(strategy.regime_avaliavel([c for _, c, _ in curto]))
        longo = [(f"d{i:04d}", 100.0, 1.0) for i in range(config.SMA_REGIME_DAYS)]
        data_sources._absorb_index_history("^BVSP", longo)
        guardado = data_sources._load_index_cache("^BVSP")
        self.assertTrue(strategy.regime_avaliavel([c for _, c, _ in guardado]))

    def test_series_on_a_different_scale_is_refused_not_glued(self):
        # Uma fonte que devolva outro indice, ou o mesmo noutra escala, faria
        # um salto de retorno que nunca existiu. Recomeca-se do vivo.
        # O pregao de 02/01 so existe no cache: e ele que denuncia se houve
        # colagem, porque sobreviveria ao lado de valores 100x menores.
        data_sources._absorb_index_history(
            "^BVSP", [("2026-01-02", 129000.0, 1.0),
                      ("2026-01-05", 130000.0, 1.0)])
        vivo = [("2026-01-05", 1300.0, 1.0), ("2026-01-06", 1310.0, 1.0)]
        junto = data_sources._absorb_index_history("^BVSP", vivo)
        self.assertEqual(junto, vivo)
        self.assertNotIn("2026-01-02", [d for d, _, _ in junto])

    def test_cache_is_not_a_crutch_for_a_missing_day(self):
        # O cache alonga a serie para tras; nao substitui o fecho de hoje.
        # Sem fonte nenhuma, o ciclo tem de falhar como falhava antes.
        data_sources._absorb_index_history(
            "^BVSP", [("2026-01-05", 130000.0, 1.0)])
        with mock.patch.object(data_sources, "fetch_brapi_daily",
                               side_effect=data_sources.DataSourceError("x")), \
             mock.patch.object(data_sources, "fetch_yahoo_daily",
                               side_effect=data_sources.DataSourceError("y")):
            with self.assertRaises(data_sources.DataSourceError):
                data_sources.fetch_b3_daily("^BVSP", is_benchmark=True)


class TestRegimeIsDeclaredNotAssumed(unittest.TestCase):
    """Uma SMA 200 sem 200 pregoes nao reprova ninguem.

    'equity_regime' devolve 'risk_on' tanto quando o filtro corre e aprova como
    quando nao ha historico para o correr — fail-open num sistema que e
    fail-closed em tudo o resto. O valor da decisao mantem-se; o que muda e que
    o relatorio passa a dizer qual dos dois casos foi.
    """

    def test_short_series_still_yields_risk_on(self):
        self.assertEqual(strategy.equity_regime([100.0] * 10), "risk_on")

    def test_but_it_is_marked_as_not_evaluated(self):
        self.assertFalse(strategy.regime_avaliavel([100.0] * 10))
        self.assertTrue(
            strategy.regime_avaliavel([100.0] * config.SMA_REGIME_DAYS))

    def test_report_says_the_filter_did_not_run(self):
        estado = {"currency": "BRL", "initial_capital": 1000.0, "cash": 10.0,
                  "inception_date": "2026-01-02",
                  "history": [{"nav": 1000.0, "benchmark_nav": 1000.0}]}
        entry = {"nav": 1000.0, "benchmark_nav": 1000.0}
        linhas = report._performance_table(estado, entry, "IBOV", None,
                                           "risk_on", regime_avaliado=False)
        regime = [ln for ln in linhas if "Regime" in ln]
        self.assertTrue(regime)
        self.assertIn("NAO avaliado", regime[0])

    def test_report_stays_plain_when_the_filter_did_run(self):
        estado = {"currency": "BRL", "initial_capital": 1000.0, "cash": 10.0,
                  "inception_date": "2026-01-02",
                  "history": [{"nav": 1000.0, "benchmark_nav": 1000.0}]}
        entry = {"nav": 1000.0, "benchmark_nav": 1000.0}
        linhas = report._performance_table(estado, entry, "IBOV", None,
                                           "risk_on", regime_avaliado=True)
        regime = [ln for ln in linhas if "Regime" in ln]
        self.assertNotIn("NAO avaliado", regime[0])
