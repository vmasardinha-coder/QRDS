"""Ciclo diario do agente sob a Carta de Operacao.

Ordem de cada ciclo, igual para todas as carteiras direcionais:
  dados -> stops -> carencias -> sinal -> tetos/piso -> ordens -> log.

Gestao de risco vem antes de procurar retorno (secao 9): os stops sao
avaliados antes de qualquer decisao de alocacao, e um ativo em carencia
nao volta a ser elegivel enquanto ela durar.
"""

from __future__ import annotations

from datetime import datetime, timezone

from . import config, data_sources, garch, portfolio, strategy, structured

Series = list[tuple[str, float, float]]


def _closes(series: Series) -> list[float]:
    return [close for _, close, _ in series]


def _is_fresh(series: Series, today: str) -> bool:
    last = datetime.strptime(series[-1][0], "%Y-%m-%d")
    now = datetime.strptime(today, "%Y-%m-%d")
    return (now - last).days <= config.STALE_PRICE_MAX_DAYS


def _fetch_universe(symbols, fetch) -> tuple[dict[str, Series], list[dict]]:
    """Descarrega o universo. Falha de dado exclui o ativo, nao inventa valor.

    Guarda o motivo de cada ausencia: sem ele nao ha como distinguir um ticker
    errado de uma indisponibilidade passageira da fonte.
    """
    universe: dict[str, Series] = {}
    failed: list[dict] = []
    for symbol in symbols:
        try:
            universe[symbol] = fetch(symbol)
        except data_sources.DataSourceError as err:
            failed.append({"symbol": symbol, "reason": str(err)[:160]})
    return universe, failed


def _sigmas(universe: dict[str, Series]) -> dict[str, float]:
    out: dict[str, float] = {}
    for symbol, series in universe.items():
        sigma = portfolio.daily_sigma(_closes(series), config.STOP_VOL_WINDOW_DAYS)
        if sigma is not None:
            out[symbol] = sigma
    return out


def _run_directional(name: str, today: str, universe: dict[str, Series],
                     failed: list[str], prices: dict[str, float],
                     bench_series: Series, decide, state: dict,
                     slippage_bps: float, cdi_rates=None) -> dict:
    """Tronco comum das carteiras direcionais (EUA, B3, crypto)."""
    weekday = datetime.strptime(today, "%Y-%m-%d").weekday()
    sigmas = _sigmas(universe)

    # 1. risco primeiro: marca d'agua e stops, antes de qualquer alocacao
    portfolio.update_high_water(state, prices)
    stops = portfolio.check_stops(state, prices, sigmas, today, slippage_bps)

    # 2. ativos em carencia por stop nao sao elegiveis neste ciclo
    cooldowns = portfolio.active_cooldowns(state, today)
    eligible = {s: series for s, series in universe.items()
                if s in prices and s not in cooldowns}

    # 3. sinal, tetos e piso
    decision = decide(eligible)
    targets = decision["weights"]
    regime = decision["regime"]

    # 4. ordens, so se houver motivo declarado
    trades: list[dict] = list(stops)
    trigger = None
    fresh_market = _is_fresh(bench_series, today)
    if fresh_market:
        trigger = portfolio.needs_rebalance(state, targets, prices, weekday, regime)
        if stops and trigger is None:
            trigger = "reinvestir apos stop"
        if trigger:
            orders = portfolio.build_orders(state, targets, prices)
            trades += portfolio.execute_orders(state, orders, today, slippage_bps)
            state["last_rebalance"] = today
            state["last_regime"] = regime

    # 5. log auditavel do que foi decidido e do que foi recusado
    log_entry = {
        "date": today,
        "regime": regime,
        "hurdle": decision["hurdle"],
        "hurdle_score": (round(decision["hurdle_score"], 4)
                         if decision["hurdle_score"] is not None else None),
        "rebalance_trigger": trigger or "nenhum (sem motivo para negociar)",
        "eligible_count": decision["eligible_count"],
        "selected": decision["selected"],
        "rejected": decision["rejected"],
        "stops": [{"symbol": t["symbol"], "reason": t.get("reason", "")}
                  for t in stops],
        "cooldowns": cooldowns,
        "data_failures": failed,
        "note": decision["note"],
        "cash_weight": decision["cash_weight"],
    }
    portfolio.log_decision(state, log_entry)
    return {"trades": trades, "decision": decision, "regime": regime,
            "log": log_entry, "targets": targets}


def run_equities(today: str) -> dict:
    """Carteira de acoes EUA — benchmark SPY."""
    bench_series = data_sources.fetch_equity_daily(config.EQUITY_BENCHMARK,
                                                  is_benchmark=True)
    universe, failed = _fetch_universe(config.EQUITY_UNIVERSE,
                                       data_sources.fetch_equity_daily)
    prices = {t: s[-1][1] for t, s in universe.items() if _is_fresh(s, today)}
    bench_price = bench_series[-1][1]

    state = portfolio.load_state("equities")
    if state is None:
        state = portfolio.new_state("equities", config.EQUITY_BENCHMARK, today,
                                    bench_price)

    bench_closes = _closes(bench_series)
    outcome = _run_directional(
        "equities", today, universe, failed, prices, bench_series,
        lambda eligible: strategy.equity_decision(eligible, bench_closes),
        state, config.EQUITY_SLIPPAGE_BPS)

    entry = portfolio.append_history(state, today, prices, bench_price)
    portfolio.save_state(state)
    return {"state": state, "entry": entry, "prices": prices,
            "benchmark_price": bench_price,
            "benchmark_last_date": bench_series[-1][0], **outcome}


def run_crypto(today: str) -> dict:
    """Carteira crypto — benchmark BTC."""
    universe, failed = _fetch_universe(
        config.CRYPTO_UNIVERSE,
        lambda a: data_sources.fetch_crypto_daily(a, config.CRYPTO_UNIVERSE[a]))
    if "BTC" not in universe:
        raise data_sources.DataSourceError("Sem serie do BTC: ciclo crypto abortado")

    prices = {a: s[-1][1] for a, s in universe.items() if _is_fresh(s, today)}
    btc_series = universe["BTC"]
    btc_price = btc_series[-1][1]

    state = portfolio.load_state("crypto")
    if state is None:
        state = portfolio.new_state("crypto", config.CRYPTO_BENCHMARK, today,
                                    btc_price)

    outcome = _run_directional(
        "crypto", today, universe, failed, prices, btc_series,
        strategy.crypto_decision, state, config.CRYPTO_SLIPPAGE_BPS)

    entry = portfolio.append_history(state, today, prices, btc_price)
    portfolio.save_state(state)
    return {"state": state, "entry": entry, "prices": prices,
            "benchmark_price": btc_price,
            "benchmark_last_date": btc_series[-1][0], **outcome}


def run_b3(today: str) -> dict:
    """Carteira de acoes B3 — obstaculo e o maior entre Ibovespa e CDI."""
    bench_series = data_sources.fetch_b3_daily(config.B3_BENCHMARK,
                                              is_benchmark=True)
    cdi_rates = data_sources.fetch_bcb_cdi_daily()
    universe, failed = _fetch_universe(config.B3_UNIVERSE,
                                       data_sources.fetch_b3_daily)
    prices = {t: s[-1][1] for t, s in universe.items() if _is_fresh(s, today)}
    bench_price = bench_series[-1][1]

    state = portfolio.load_state("b3")
    if state is None:
        state = portfolio.new_state(
            "b3", config.B3_BENCHMARK, today, bench_price, currency="BRL",
            initial_capital=config.B3_INITIAL_CAPITAL_BRL,
            benchmark2_symbol=config.B3_BENCHMARK2)

    portfolio.accrue_cash_cdi(state, cdi_rates, today)

    # obstaculo do CDI medido na mesma janela do momentum (12-1). Sem janela
    # completa nao se calcula: um acumulado de menos dias seria um obstaculo
    # artificialmente baixo, e baixar a fasquia em silencio e pior que nao a ter.
    window = config.EQUITY_MOM_LONG_DAYS - config.EQUITY_MOM_SKIP_DAYS
    cdi_window = None
    if len(cdi_rates) >= window:
        cdi_window = 1.0
        for _, rate in cdi_rates[-window:]:
            cdi_window *= 1.0 + rate / 100.0
        cdi_window -= 1.0

    bench_closes = _closes(bench_series)
    outcome = _run_directional(
        "b3", today, universe, failed, prices, bench_series,
        lambda eligible: strategy.b3_decision(eligible, bench_closes, cdi_window),
        state, config.B3_SLIPPAGE_BPS)

    cdi_factor = data_sources.cdi_factor_since(cdi_rates,
                                               state["inception_date"], today)
    entry = portfolio.append_history(state, today, prices, bench_price,
                                     benchmark2_factor=cdi_factor)
    portfolio.save_state(state)
    return {"state": state, "entry": entry, "prices": prices,
            "benchmark_price": bench_price,
            "benchmark_last_date": bench_series[-1][0], **outcome}


def run_b3_structured(today: str) -> dict:
    """Carteira B3 estruturadas: financiamento coberto em BOVA11 vs CDI."""
    underlying = config.B3S_UNDERLYING
    series = data_sources.fetch_b3_daily(underlying)
    bench_series = data_sources.fetch_b3_daily(config.B3_BENCHMARK,
                                              is_benchmark=True)
    cdi_rates = data_sources.fetch_bcb_cdi_daily()

    spot = series[-1][1]
    prices = {underlying: spot}
    bench_price = bench_series[-1][1]
    fresh = _is_fresh(series, today)

    state = portfolio.load_state("b3_estruturadas")
    if state is None:
        state = portfolio.new_state(
            "b3_estruturadas", config.B3_BENCHMARK, today, bench_price,
            currency="BRL", initial_capital=config.B3S_INITIAL_CAPITAL_BRL,
            benchmark2_symbol=config.B3_BENCHMARK2)

    portfolio.accrue_cash_cdi(state, cdi_rates, today)

    closes = _closes(series)
    vol_realized = structured.realized_vol(closes, config.B3S_VOL_WINDOW_DAYS)
    # GARCH(1,1) como calibrador principal; fallback para a realizada
    try:
        sigma = garch.forecast_avg_vol(closes, config.B3S_GARCH_HORIZON_DAYS)
        vol_source = "GARCH(1,1)"
    except (ValueError, ZeroDivisionError, OverflowError):
        sigma = vol_realized
        vol_source = f"realizada {config.B3S_VOL_WINDOW_DAYS}d"
    rate_annual = structured.annual_rate_from_cdi(cdi_rates[-1][1])

    trades: list[dict] = []
    actions: list[str] = []
    if fresh:
        if underlying not in state["positions"]:
            orders = portfolio.build_orders(state, {underlying: 1.0}, prices)
            trades += portfolio.execute_orders(state, orders, today,
                                               config.B3S_SLIPPAGE_BPS)
            state["last_rebalance"] = today
            actions.append(f"montagem da posicao comprada em {underlying}")
        settle = structured.settle_expired_call(state, spot, today)
        if settle:
            trades.append(settle)
            actions.append("liquidacao da call vencida")
        if not state.get("short_call") and underlying in state["positions"]:
            trades.append(structured.sell_new_call(state, spot, sigma,
                                                   rate_annual, today))
            actions.append("venda de nova call coberta")

    liability = structured.short_call_liability(state, spot, sigma,
                                                rate_annual, today)
    nav_net = portfolio.nav(state, prices) - liability

    extra_lines: list[str] = []
    sc = state.get("short_call")
    if sc:
        extra_lines.append(
            f"Call vendida (premio modelado): strike R$ {sc['strike']:.2f}, "
            f"vence {sc['expiry']}, premio R$ {sc['premium_unit']:.4f}/un, "
            f"valor atual da obrigacao R$ {liability:,.2f}")
    extra_lines.append(
        f"Volatilidade usada na call ({vol_source}): {sigma*100:.1f}% a.a. "
        f"| realizada {config.B3S_VOL_WINDOW_DAYS}d: {vol_realized*100:.1f}% a.a. "
        f"| CDI: {cdi_rates[-1][1]:.4f}% a.d.")

    log_entry = {
        "date": today, "regime": "-", "hurdle": "CDI",
        "rebalance_trigger": "; ".join(actions) or "nenhum (call em curso)",
        "vol_source": vol_source, "sigma": round(sigma, 4),
        "vol_realized": round(vol_realized, 4),
        "short_call": sc, "data_failures": [],
        "selected": [{"symbol": underlying, "weight": 1.0}],
        "rejected": [], "stops": [], "cooldowns": {}, "note": "",
    }
    portfolio.log_decision(state, log_entry)

    cdi_factor = data_sources.cdi_factor_since(cdi_rates,
                                               state["inception_date"], today)
    entry = portfolio.append_history(state, today, prices, bench_price,
                                     benchmark2_factor=cdi_factor,
                                     nav_override=nav_net)
    portfolio.save_state(state)
    return {
        "state": state, "entry": entry, "trades": trades, "regime": "-",
        "targets": {underlying: 1.0}, "prices": prices,
        "decision": {"note": "", "rejected": [], "eligible_count": 1},
        "log": log_entry, "benchmark_price": bench_price,
        "benchmark_last_date": bench_series[-1][0], "extra_lines": extra_lines,
    }


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
