"""Estado da carteira, execucao simulada de ordens e historico.

O estado vive em trading_agent/state/<nome>.json e e versionado no git,
por isso sobrevive entre execucoes do workflow diario.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from . import config

STATE_DIR = Path(__file__).resolve().parent / "state"


def new_state(name: str, benchmark_symbol: str, date: str,
              benchmark_price: float, currency: str = "USD",
              initial_capital: float | None = None,
              benchmark2_symbol: str | None = None) -> dict:
    capital = initial_capital if initial_capital is not None else config.INITIAL_CAPITAL_USD
    state = {
        "name": name,
        "currency": currency,
        "initial_capital": capital,
        "inception_date": date,
        "cash": capital,
        "positions": {},          # symbol -> {"qty": float, "avg_cost": float}
        "benchmark": {"symbol": benchmark_symbol, "inception_price": benchmark_price},
        "last_rebalance": None,
        "last_regime": None,
        "history": [],            # [{"date", "nav", "benchmark_nav"}]
        "trades": [],             # [{"date", "symbol", "side", "qty", "price", "value"}]
    }
    if benchmark2_symbol is not None:
        # benchmark2 (CDI) e calculado como fator acumulado desde a inception,
        # por isso basta guardar o simbolo
        state["benchmark2"] = {"symbol": benchmark2_symbol}
    return state


def daily_sigma(closes: list[float], window: int) -> float | None:
    """Desvio-padrao dos retornos diarios (base do stop estatistico)."""
    if len(closes) < window + 1:
        return None
    tail = closes[-(window + 1):]
    rets = [tail[i + 1] / tail[i] - 1.0 for i in range(len(tail) - 1)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return var ** 0.5


def update_high_water(state: dict, prices: dict[str, float]) -> None:
    """Marca d'agua por posicao — referencia do stop movel."""
    for symbol, pos in state["positions"].items():
        price = prices.get(symbol)
        if price is None:
            continue
        pos["high_water"] = max(pos.get("high_water", price), price)


def check_stops(state: dict, prices: dict[str, float],
                sigmas: dict[str, float], today: str,
                slippage_bps: float) -> list[dict]:
    """Stop proporcional a volatilidade do proprio ativo (secao 4 da Carta).

    Vende a posicao quando a queda desde a marca d'agua excede
    STOP_SIGMA_MULTIPLE x desvio-padrao diario, e poe o ativo em carencia
    para nao ser recomprado no rebalanceio seguinte.
    """
    triggered: list[dict] = []
    cooldown = state.setdefault("cooldown", {})
    for symbol in list(state["positions"]):
        price = prices.get(symbol)
        sigma = sigmas.get(symbol)
        if price is None or sigma is None or sigma <= 0:
            continue
        pos = state["positions"][symbol]
        high = pos.get("high_water", price)
        limit = config.STOP_SIGMA_MULTIPLE * sigma
        drawdown = 1.0 - price / high if high > 0 else 0.0
        if drawdown <= limit:
            continue
        qty = pos["qty"]
        executed = execute_orders(
            state, [{"symbol": symbol, "side": "sell", "qty": qty,
                     "ref_price": price}], today, slippage_bps)
        until = (datetime.strptime(today, "%Y-%m-%d")
                 + timedelta(days=config.STOP_COOLDOWN_DAYS)).strftime("%Y-%m-%d")
        cooldown[symbol] = until
        for trade in executed:
            trade["reason"] = (f"stop: queda {drawdown*100:.1f}% > "
                               f"{config.STOP_SIGMA_MULTIPLE:.0f}x sigma "
                               f"({limit*100:.1f}%); carencia ate {until}")
            triggered.append(trade)
    return triggered


def active_cooldowns(state: dict, today: str) -> dict[str, str]:
    """Ativos em carencia por stop, limpando os ja expirados."""
    cooldown = state.setdefault("cooldown", {})
    for symbol, until in list(cooldown.items()):
        if until <= today:
            del cooldown[symbol]
    return dict(cooldown)


def log_decision(state: dict, entry: dict) -> None:
    """Guarda a decisao do dia para auditoria posterior (secao 8 da Carta)."""
    log = state.setdefault("decision_log", [])
    if log and log[-1].get("date") == entry.get("date"):
        log[-1] = entry
    else:
        log.append(entry)
    del log[: max(0, len(log) - config.DECISION_LOG_MAX_ENTRIES)]


def accrue_cash_cdi(state: dict, cdi_rates: list[tuple[str, float]],
                    today: str) -> None:
    """Rende a caixa em BRL ao CDI para os dias uteis ainda nao acumulados."""
    last = state.get("last_accrual_date") or state["inception_date"]
    for date, rate in cdi_rates:
        if last < date <= today:
            if state["cash"] > 0:
                state["cash"] *= 1.0 + rate / 100.0
            state["last_accrual_date"] = date


def state_path(name: str) -> Path:
    return STATE_DIR / f"{name}.json"


def load_state(name: str) -> dict | None:
    path = state_path(name)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(state["name"])
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def nav(state: dict, prices: dict[str, float]) -> float:
    total = state["cash"]
    for symbol, pos in state["positions"].items():
        price = prices.get(symbol)
        if price is None:
            price = pos["avg_cost"]  # sem preco fresco, usa custo (conservador)
        total += pos["qty"] * price
    return total


def current_weights(state: dict, prices: dict[str, float]) -> dict[str, float]:
    total = nav(state, prices)
    if total <= 0:
        return {}
    out = {}
    for symbol, pos in state["positions"].items():
        price = prices.get(symbol, pos["avg_cost"])
        out[symbol] = pos["qty"] * price / total
    return out


def build_orders(state: dict, target_weights: dict[str, float],
                 prices: dict[str, float]) -> list[dict]:
    """Diferenca entre pesos atuais e alvo -> lista de ordens."""
    total = nav(state, prices)
    orders: list[dict] = []
    symbols = set(state["positions"]) | set(target_weights)
    for symbol in sorted(symbols):
        price = prices.get(symbol)
        if price is None or price <= 0:
            continue
        held_qty = state["positions"].get(symbol, {}).get("qty", 0.0)
        target_value = target_weights.get(symbol, 0.0) * total
        delta_value = target_value - held_qty * price
        if abs(delta_value) < config.MIN_TRADE_VALUE_USD:
            continue
        side = "buy" if delta_value > 0 else "sell"
        qty = abs(delta_value) / price
        if side == "sell":
            qty = min(qty, held_qty)
            if qty <= 0:
                continue
        orders.append({"symbol": symbol, "side": side, "qty": qty, "ref_price": price})
    # vende primeiro para libertar caixa para as compras
    orders.sort(key=lambda o: 0 if o["side"] == "sell" else 1)
    return orders


def execute_orders(state: dict, orders: list[dict], date: str,
                   slippage_bps: float) -> list[dict]:
    """Executa ordens ao preco de referencia com slippage modelado."""
    executed: list[dict] = []
    slip = slippage_bps / 10_000.0
    for order in orders:
        symbol, side, qty = order["symbol"], order["side"], order["qty"]
        price = order["ref_price"] * (1 + slip if side == "buy" else 1 - slip)
        value = qty * price
        if side == "buy":
            if value > state["cash"]:
                value = state["cash"]
                qty = value / price
            if value < config.MIN_TRADE_VALUE_USD / 2:
                continue
            state["cash"] -= value
            pos = state["positions"].setdefault(
                symbol, {"qty": 0.0, "avg_cost": 0.0, "high_water": price})
            new_qty = pos["qty"] + qty
            pos["avg_cost"] = (pos["qty"] * pos["avg_cost"] + value) / new_qty
            pos["qty"] = new_qty
        else:
            pos = state["positions"].get(symbol)
            if pos is None:
                continue
            qty = min(qty, pos["qty"])
            value = qty * price
            state["cash"] += value
            pos["qty"] -= qty
            if pos["qty"] * price < 1.0:
                del state["positions"][symbol]
        trade = {"date": date, "symbol": symbol, "side": side,
                 "qty": round(qty, 8), "price": round(price, 6),
                 "value": round(value, 2)}
        state["trades"].append(trade)
        executed.append(trade)
    return executed


def append_history(state: dict, date: str, prices: dict[str, float],
                   benchmark_price: float,
                   benchmark2_factor: float | None = None,
                   nav_override: float | None = None) -> dict:
    bench = state["benchmark"]
    benchmark_nav = state["initial_capital"] * benchmark_price / bench["inception_price"]
    total = nav_override if nav_override is not None else nav(state, prices)
    entry = {"date": date, "nav": round(total, 2),
             "benchmark_nav": round(benchmark_nav, 2)}
    if benchmark2_factor is not None and "benchmark2" in state:
        entry["benchmark2_nav"] = round(
            state["initial_capital"] * benchmark2_factor, 2)
    if state["history"] and state["history"][-1]["date"] == date:
        state["history"][-1] = entry
    else:
        state["history"].append(entry)
    return entry


def needs_rebalance(state: dict, target_weights: dict[str, float],
                    prices: dict[str, float], today_weekday: int,
                    regime: str) -> str | None:
    """Devolve o motivo do rebalanceio (para o log) ou None se nao ha motivo."""
    if state["last_rebalance"] is None:
        return "primeira execucao da carteira"
    if regime != state.get("last_regime"):
        return f"mudanca de regime: {state.get('last_regime')} -> {regime}"
    if today_weekday == config.REBALANCE_WEEKDAY:
        return "cadencia semanal (segunda-feira)"
    weights = current_weights(state, prices)
    for symbol, target in target_weights.items():
        if target <= 0:
            continue
        actual = weights.get(symbol, 0.0)
        if abs(actual - target) / target > config.DRIFT_REBALANCE_THRESHOLD:
            return (f"desvio de peso em {symbol}: {actual*100:.1f}% vs alvo "
                    f"{target*100:.1f}%")
    return None
