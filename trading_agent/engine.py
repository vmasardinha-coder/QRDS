"""Ciclo diario do agente: dados -> sinal -> ordens -> estado -> historico."""

from __future__ import annotations

from datetime import datetime, timezone

from . import config, data_sources, portfolio, strategy

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
    bench_series = data_sources.fetch_stooq_daily(config.EQUITY_BENCHMARK)

    universe: dict[str, Series] = {}
    failed: list[str] = []
    for ticker in config.EQUITY_UNIVERSE:
        try:
            universe[ticker] = data_sources.fetch_stooq_daily(ticker)
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


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
