"""Estado da carteira, execucao simulada de ordens e historico.

O estado vive em trading_agent/state/<nome>.json e e versionado no git,
por isso sobrevive entre execucoes do workflow diario.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config

STATE_DIR = Path(__file__).resolve().parent / "state"


def new_state(name: str, benchmark_symbol: str, date: str,
              benchmark_price: float) -> dict:
    return {
        "name": name,
        "currency": "USD",
        "initial_capital": config.INITIAL_CAPITAL_USD,
        "inception_date": date,
        "cash": config.INITIAL_CAPITAL_USD,
        "positions": {},          # symbol -> {"qty": float, "avg_cost": float}
        "benchmark": {"symbol": benchmark_symbol, "inception_price": benchmark_price},
        "last_rebalance": None,
        "last_regime": None,
        "history": [],            # [{"date", "nav", "benchmark_nav"}]
        "trades": [],             # [{"date", "symbol", "side", "qty", "price", "value"}]
    }


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
            pos = state["positions"].setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0})
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
                   benchmark_price: float) -> dict:
    bench = state["benchmark"]
    benchmark_nav = state["initial_capital"] * benchmark_price / bench["inception_price"]
    entry = {"date": date, "nav": round(nav(state, prices), 2),
             "benchmark_nav": round(benchmark_nav, 2)}
    if state["history"] and state["history"][-1]["date"] == date:
        state["history"][-1] = entry
    else:
        state["history"].append(entry)
    return entry


def needs_rebalance(state: dict, target_weights: dict[str, float],
                    prices: dict[str, float], today_weekday: int,
                    regime: str) -> bool:
    if state["last_rebalance"] is None:
        return True
    if regime != state.get("last_regime"):
        return True
    if today_weekday == config.REBALANCE_WEEKDAY:
        return True
    weights = current_weights(state, prices)
    for symbol, target in target_weights.items():
        if target <= 0:
            continue
        actual = weights.get(symbol, 0.0)
        if abs(actual - target) / target > config.DRIFT_REBALANCE_THRESHOLD:
            return True
    return False
