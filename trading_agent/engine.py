"""Ciclo diario do agente: dados -> sinal -> ordens -> estado -> historico."""

from __future__ import annotations

from datetime import datetime, timezone

from . import config, data_sources, portfolio, strategy, structured

Series = list[tuple[str, float]]


def _closes(series: Series) -> list[float]:
    return [close for _, close in series]


def _is_fresh(series: Series, today: str) -> bool:
    last = datetime.strptime(series[-1][0], "%Y-%m-%d")
    now = datetime.strptime(today, "%Y-%m-%d")
    return (now - last).days <= config.STALE_PRICE_MAX_DAYS


def run_equities(today: str) -> dict:
    """Executa o ciclo da carteira de acoes. Devolve resumo para o relatorio."""
    weekday = datetime.strptime(today, "%Y-%m-%d").weekday()
    bench_series = data_sources.fetch_equity_daily(config.EQUITY_BENCHMARK)

    universe: dict[str, Series] = {}
    failed: list[str] = []
    for ticker in config.EQUITY_UNIVERSE:
        try:
            universe[ticker] = data_sources.fetch_equity_daily(ticker)
        except data_sources.DataSourceError:
            failed.append(ticker)

    prices = {t: s[-1][1] for t, s in universe.items() if _is_fresh(s, today)}
    bench_price = bench_series[-1][1]

    state = portfolio.load_state("equities")
    if state is None:
        state = portfolio.new_state("equities", config.EQUITY_BENCHMARK, today, bench_price)

    closes = {t: _closes(s) for t, s in universe.items() if t in prices}
    targets, regime = strategy.equity_target_weights(closes, _closes(bench_series))

    trades: list[dict] = []
    rebalanced = False
    market_open_data = _is_fresh(bench_series, today)
    if market_open_data and portfolio.needs_rebalance(state, targets, prices, weekday, regime):
        orders = portfolio.build_orders(state, targets, prices)
        trades = portfolio.execute_orders(state, orders, today, config.EQUITY_SLIPPAGE_BPS)
        state["last_rebalance"] = today
        state["last_regime"] = regime
        rebalanced = True

    entry = portfolio.append_history(state, today, prices, bench_price)
    portfolio.save_state(state)
    return {
        "state": state, "entry": entry, "trades": trades, "regime": regime,
        "targets": targets, "prices": prices, "rebalanced": rebalanced,
        "data_failures": failed, "benchmark_price": bench_price,
        "benchmark_last_date": bench_series[-1][0],
    }


def run_crypto(today: str) -> dict:
    """Executa o ciclo da carteira crypto. Devolve resumo para o relatorio."""
    weekday = datetime.strptime(today, "%Y-%m-%d").weekday()
    universe: dict[str, Series] = {}
    failed: list[str] = []
    for asset, gecko_id in config.CRYPTO_UNIVERSE.items():
        try:
            universe[asset] = data_sources.fetch_crypto_daily(asset, gecko_id)
        except data_sources.DataSourceError:
            failed.append(asset)

    if "BTC" not in universe:
        raise data_sources.DataSourceError("Sem serie do BTC: ciclo crypto abortado")

    prices = {a: s[-1][1] for a, s in universe.items() if _is_fresh(s, today)}
    btc_price = universe["BTC"][-1][1]

    state = portfolio.load_state("crypto")
    if state is None:
        state = portfolio.new_state("crypto", config.CRYPTO_BENCHMARK, today, btc_price)

    closes = {a: _closes(s) for a, s in universe.items() if a in prices}
    targets, regime = strategy.crypto_target_weights(closes)

    trades: list[dict] = []
    rebalanced = False
    if "BTC" in prices and portfolio.needs_rebalance(state, targets, prices, weekday, regime):
        orders = portfolio.build_orders(state, targets, prices)
        trades = portfolio.execute_orders(state, orders, today, config.CRYPTO_SLIPPAGE_BPS)
        state["last_rebalance"] = today
        state["last_regime"] = regime
        rebalanced = True

    entry = portfolio.append_history(state, today, prices, btc_price)
    portfolio.save_state(state)
    return {
        "state": state, "entry": entry, "trades": trades, "regime": regime,
        "targets": targets, "prices": prices, "rebalanced": rebalanced,
        "data_failures": failed, "benchmark_price": btc_price,
        "benchmark_last_date": universe["BTC"][-1][0],
    }


def run_b3(today: str) -> dict:
    """Ciclo da carteira de acoes B3 (momentum vs Ibovespa, caixa rende CDI)."""
    weekday = datetime.strptime(today, "%Y-%m-%d").weekday()
    bench_series = data_sources.fetch_b3_daily(config.B3_BENCHMARK)
    cdi_rates = data_sources.fetch_bcb_cdi_daily()
    cdi_idx = data_sources.cdi_index(cdi_rates)

    universe: dict[str, Series] = {}
    failed: list[str] = []
    for ticker in config.B3_UNIVERSE:
        try:
            universe[ticker] = data_sources.fetch_b3_daily(ticker)
        except data_sources.DataSourceError:
            failed.append(ticker)

    prices = {t: s[-1][1] for t, s in universe.items() if _is_fresh(s, today)}
    bench_price = bench_series[-1][1]

    state = portfolio.load_state("b3")
    if state is None:
        state = portfolio.new_state(
            "b3", config.B3_BENCHMARK, today, bench_price, currency="BRL",
            initial_capital=config.B3_INITIAL_CAPITAL_BRL,
            benchmark2_symbol=config.B3_BENCHMARK2,
            benchmark2_index=cdi_idx[-1][1])

    portfolio.accrue_cash_cdi(state, cdi_rates, today)

    closes = {t: _closes(s) for t, s in universe.items() if t in prices}
    targets, regime = strategy.b3_target_weights(closes, _closes(bench_series))

    trades: list[dict] = []
    rebalanced = False
    market_open_data = _is_fresh(bench_series, today)
    if market_open_data and portfolio.needs_rebalance(state, targets, prices, weekday, regime):
        orders = portfolio.build_orders(state, targets, prices)
        trades = portfolio.execute_orders(state, orders, today, config.B3_SLIPPAGE_BPS)
        state["last_rebalance"] = today
        state["last_regime"] = regime
        rebalanced = True

    entry = portfolio.append_history(state, today, prices, bench_price,
                                     benchmark2_index=cdi_idx[-1][1])
    portfolio.save_state(state)
    return {
        "state": state, "entry": entry, "trades": trades, "regime": regime,
        "targets": targets, "prices": prices, "rebalanced": rebalanced,
        "data_failures": failed, "benchmark_price": bench_price,
        "benchmark_last_date": bench_series[-1][0],
    }


def run_b3_structured(today: str) -> dict:
    """Ciclo da carteira B3 estruturadas: financiamento coberto em BOVA11."""
    underlying = config.B3S_UNDERLYING
    series = data_sources.fetch_b3_daily(underlying)
    bench_series = data_sources.fetch_b3_daily(config.B3_BENCHMARK)
    cdi_rates = data_sources.fetch_bcb_cdi_daily()
    cdi_idx = data_sources.cdi_index(cdi_rates)

    spot = series[-1][1]
    prices = {underlying: spot}
    bench_price = bench_series[-1][1]
    fresh = _is_fresh(series, today)

    state = portfolio.load_state("b3_estruturadas")
    if state is None:
        state = portfolio.new_state(
            "b3_estruturadas", config.B3_BENCHMARK, today, bench_price,
            currency="BRL", initial_capital=config.B3S_INITIAL_CAPITAL_BRL,
            benchmark2_symbol=config.B3_BENCHMARK2,
            benchmark2_index=cdi_idx[-1][1])

    portfolio.accrue_cash_cdi(state, cdi_rates, today)

    sigma = structured.realized_vol(_closes(series), config.B3S_VOL_WINDOW_DAYS)
    rate_annual = structured.annual_rate_from_cdi(cdi_rates[-1][1])

    trades: list[dict] = []
    extra_lines: list[str] = []
    if fresh:
        if underlying not in state["positions"]:
            orders = portfolio.build_orders(state, {underlying: 1.0}, prices)
            trades += portfolio.execute_orders(state, orders, today,
                                               config.B3S_SLIPPAGE_BPS)
            state["last_rebalance"] = today
        settle = structured.settle_expired_call(state, spot, today)
        if settle:
            trades.append(settle)
        if not state.get("short_call") and underlying in state["positions"]:
            trades.append(structured.sell_new_call(state, spot, sigma,
                                                   rate_annual, today))

    liability = structured.short_call_liability(state, spot, sigma,
                                                rate_annual, today)
    nav_net = portfolio.nav(state, prices) - liability

    sc = state.get("short_call")
    if sc:
        extra_lines.append(
            f"Call vendida (premio modelado): strike R$ {sc['strike']:.2f}, "
            f"vence {sc['expiry']}, premio R$ {sc['premium_unit']:.4f}/un, "
            f"valor atual da obrigacao R$ {liability:,.2f}")
    extra_lines.append(
        f"Volatilidade realizada {config.B3S_VOL_WINDOW_DAYS}d: {sigma*100:.1f}% a.a. "
        f"| CDI: {cdi_rates[-1][1]:.4f}% a.d.")

    entry = portfolio.append_history(state, today, prices, bench_price,
                                     benchmark2_index=cdi_idx[-1][1],
                                     nav_override=nav_net)
    portfolio.save_state(state)
    return {
        "state": state, "entry": entry, "trades": trades, "regime": "-",
        "targets": {}, "prices": prices, "rebalanced": bool(trades),
        "data_failures": [], "benchmark_price": bench_price,
        "benchmark_last_date": bench_series[-1][0],
        "extra_lines": extra_lines,
    }


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
