"""Operacoes estruturadas B3: financiamento coberto (covered call) em BOVA11.

Nao existe fonte gratuita fiavel de cotacoes de opcoes da B3, por isso os
premios sao MODELADOS via Black-Scholes com volatilidade realizada do
subjacente e o CDI como taxa livre de risco. O relatorio diario declara isso.

Mecanica do financiamento:
  - carteira 100% comprada em BOVA11;
  - vende call ~3% OTM com prazo de 30 dias sobre a posicao inteira,
    creditando o premio em caixa;
  - no vencimento, liquidacao financeira: se o spot ficou acima do strike,
    paga (spot - strike) * qtd; o premio fica sempre;
  - vende nova call e repete. A caixa rende CDI.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from . import config

TRADING_DAYS_PER_YEAR = 252


def realized_vol(closes: list[float], window: int) -> float:
    """Volatilidade realizada anualizada a partir de fechos diarios."""
    if len(closes) < window + 1:
        raise ValueError("historico insuficiente para volatilidade")
    tail = closes[-(window + 1):]
    rets = [math.log(tail[i + 1] / tail[i]) for i in range(len(tail) - 1)]
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var * TRADING_DAYS_PER_YEAR)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_call_price(spot: float, strike: float, years: float,
                  rate: float, sigma: float) -> float:
    """Preco Black-Scholes de uma call europeia."""
    if years <= 0:
        return max(spot - strike, 0.0)
    if sigma <= 0:
        return max(spot - strike * math.exp(-rate * years), 0.0)
    d1 = (math.log(spot / strike) + (rate + sigma ** 2 / 2) * years) / (sigma * math.sqrt(years))
    d2 = d1 - sigma * math.sqrt(years)
    return spot * _norm_cdf(d1) - strike * math.exp(-rate * years) * _norm_cdf(d2)


def annual_rate_from_cdi(daily_pct: float) -> float:
    """Taxa anual continua equivalente a partir do CDI diario (% a.d.)."""
    return math.log((1.0 + daily_pct / 100.0) ** TRADING_DAYS_PER_YEAR)


def years_to_expiry(today: str, expiry: str) -> float:
    d0 = datetime.strptime(today, "%Y-%m-%d")
    d1 = datetime.strptime(expiry, "%Y-%m-%d")
    return max((d1 - d0).days, 0) / 365.0


def settle_expired_call(state: dict, spot: float, today: str) -> dict | None:
    """Liquida financeiramente a call vendida se ja venceu. Devolve o trade."""
    sc = state.get("short_call")
    if not sc or today < sc["expiry"]:
        return None
    payoff = max(spot - sc["strike"], 0.0) * sc["qty"]
    state["cash"] -= payoff
    state["short_call"] = None
    trade = {"date": today, "symbol": f"CALL {sc['strike']:.2f} (venc.)",
             "side": "settle", "qty": sc["qty"], "price": spot,
             "value": round(-payoff, 2)}
    state["trades"].append(trade)
    return trade


def sell_new_call(state: dict, spot: float, sigma: float, rate_annual: float,
                  today: str) -> dict:
    """Vende call OTM coberta sobre a posicao inteira; credita premio modelado."""
    qty = state["positions"][config.B3S_UNDERLYING]["qty"]
    strike = round(spot * config.B3S_CALL_OTM, 2)
    tenor_years = config.B3S_CALL_TENOR_DAYS / 365.0
    premium_unit = bs_call_price(spot, strike, tenor_years, rate_annual, sigma)
    premium = premium_unit * qty
    expiry = (datetime.strptime(today, "%Y-%m-%d")
              + timedelta(days=config.B3S_CALL_TENOR_DAYS)).strftime("%Y-%m-%d")
    state["cash"] += premium
    state["short_call"] = {"strike": strike, "expiry": expiry, "qty": qty,
                           "premium_unit": round(premium_unit, 4),
                           "sold_on": today, "sigma": round(sigma, 4)}
    trade = {"date": today, "symbol": f"CALL {strike:.2f} venc. {expiry}",
             "side": "sell", "qty": qty, "price": round(premium_unit, 4),
             "value": round(premium, 2)}
    state["trades"].append(trade)
    return trade


def short_call_liability(state: dict, spot: float, sigma: float,
                         rate_annual: float, today: str) -> float:
    """Valor de mercado (modelado) da call vendida, a abater ao NAV."""
    sc = state.get("short_call")
    if not sc:
        return 0.0
    years = years_to_expiry(today, sc["expiry"])
    return bs_call_price(spot, sc["strike"], years, rate_annual, sigma) * sc["qty"]
