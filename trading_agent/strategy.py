"""Estrategias das duas carteiras.

Acoes  : momentum transversal 12-1 sobre large caps, top N em pesos iguais,
         com filtro de regime (SPY vs SMA 200) a reduzir exposicao.
Crypto : nucleo em BTC + tilt para as alts com momentum superior ao BTC,
         com filtro de regime (BTC vs SMA 200) a reduzir exposicao.

Ambas devolvem pesos-alvo por ativo (fraccao do NAV); o resto fica em caixa.
"""

from __future__ import annotations

from . import config

Series = list[tuple[str, float]]


def sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def equity_momentum_score(closes: list[float]) -> float | None:
    """Momentum 12-1: retorno da janela longa excluindo o mes mais recente."""
    if len(closes) < config.EQUITY_MIN_HISTORY_DAYS:
        return None
    recent = closes[-(config.EQUITY_MOM_SKIP_DAYS + 1)]
    old = closes[-(config.EQUITY_MOM_LONG_DAYS + 1)]
    if old <= 0:
        return None
    return recent / old - 1.0


def equity_regime(benchmark_closes: list[float]) -> str:
    avg = sma(benchmark_closes, config.SMA_REGIME_DAYS)
    if avg is None or benchmark_closes[-1] >= avg:
        return "risk_on"
    return "risk_off"


def equity_target_weights(universe_closes: dict[str, list[float]],
                          benchmark_closes: list[float]) -> tuple[dict[str, float], str]:
    """Pesos-alvo da carteira de acoes e regime atual."""
    scores: dict[str, float] = {}
    for ticker, closes in universe_closes.items():
        score = equity_momentum_score(closes)
        if score is not None:
            scores[ticker] = score
    ranked = sorted(scores, key=scores.get, reverse=True)[: config.EQUITY_TOP_N]
    regime = equity_regime(benchmark_closes)
    exposure = 1.0 if regime == "risk_on" else config.EQUITY_RISK_OFF_EXPOSURE
    if not ranked:
        return {}, regime
    weight = exposure / len(ranked)
    return {t: weight for t in ranked}, regime


def crypto_momentum_score(closes: list[float]) -> float | None:
    if len(closes) < config.CRYPTO_MIN_HISTORY_DAYS:
        return None
    short_old = closes[-(config.CRYPTO_MOM_SHORT_DAYS + 1)]
    long_old = closes[-(config.CRYPTO_MOM_LONG_DAYS + 1)]
    if short_old <= 0 or long_old <= 0:
        return None
    short_ret = closes[-1] / short_old - 1.0
    long_ret = closes[-1] / long_old - 1.0
    return 0.5 * short_ret + 0.5 * long_ret


def crypto_regime(btc_closes: list[float]) -> str:
    avg = sma(btc_closes, config.SMA_REGIME_DAYS)
    if avg is None or btc_closes[-1] >= avg:
        return "risk_on"
    return "risk_off"


def crypto_target_weights(universe_closes: dict[str, list[float]]) -> tuple[dict[str, float], str]:
    """Pesos-alvo da carteira crypto e regime atual.

    BTC e o nucleo; as (ate) CRYPTO_MAX_ALTS alts com momentum acima do BTC
    partilham o resto da parte investida. Sem alts qualificadas -> 100% BTC.
    """
    btc_closes = universe_closes.get("BTC", [])
    regime = crypto_regime(btc_closes)
    exposure = 1.0 if regime == "risk_on" else config.CRYPTO_RISK_OFF_EXPOSURE

    btc_score = crypto_momentum_score(btc_closes)
    if btc_score is None:
        # sem historico suficiente do BTC nao ha decisao: tudo em BTC
        return {"BTC": exposure}, regime

    alt_scores: dict[str, float] = {}
    for asset, closes in universe_closes.items():
        if asset == "BTC":
            continue
        score = crypto_momentum_score(closes)
        if score is not None and score > btc_score:
            alt_scores[asset] = score
    chosen = sorted(alt_scores, key=alt_scores.get, reverse=True)[: config.CRYPTO_MAX_ALTS]

    weights: dict[str, float] = {}
    if chosen:
        alt_budget = exposure * (1.0 - config.CRYPTO_BTC_CORE_WEIGHT)
        per_alt = alt_budget / len(chosen)
        weights = {a: per_alt for a in chosen}
        weights["BTC"] = exposure * config.CRYPTO_BTC_CORE_WEIGHT
    else:
        weights["BTC"] = exposure
    return weights, regime
