"""Estrategias das carteiras, sob a Carta de Operacao.

Regras estruturais aplicadas a todas as carteiras direcionais:
  1. filtro de regime (SMA 200) decide QUANTO risco se aloca;
  2. filtro de liquidez exclui o que nao e executavel (secao 5);
  3. forca relativa: o ativo tem de bater o proprio benchmark, nao apenas
     os pares — momentum absoluto sozinho persegue quem ja subiu (secao 5);
  4. teto por posicao ativa, que nunca e ultrapassado (secao 4);
  5. piso de diversificacao: candidatos a menos -> caixa, nunca afrouxar
     o criterio (secao 4).

Cada funcao devolve um dicionario de decisao com pesos, selecionados e
rejeitados com motivo, para o log auditavel da secao 8.
"""

from __future__ import annotations

from statistics import median

from . import config

Series = list[tuple[str, float, float]]


def sma(closes: list[float], window: int) -> float | None:
    if len(closes) < window:
        return None
    return sum(closes[-window:]) / window


def median_turnover(series: Series, window: int) -> float:
    """Mediana de (preco x volume) diario — proxy de liquidez executavel."""
    tail = series[-window:]
    values = [close * volume for _, close, volume in tail]
    if not values:
        return 0.0
    return median(values)


def equity_momentum_score(closes: list[float]) -> float | None:
    """Momentum 12-1: retorno da janela longa excluindo o mes mais recente."""
    if len(closes) < config.EQUITY_MIN_HISTORY_DAYS:
        return None
    recent = closes[-(config.EQUITY_MOM_SKIP_DAYS + 1)]
    old = closes[-(config.EQUITY_MOM_LONG_DAYS + 1)]
    if old <= 0:
        return None
    return recent / old - 1.0


def regime_avaliavel(closes: list[float]) -> bool:
    """Ha pregoes que cheguem para a SMA 200 dizer alguma coisa?

    Separado de 'equity_regime' de proposito: sem isto, uma serie curta devolve
    'risk_on' — o mesmo valor que uma SMA calculada a serio — e o relatorio
    escrevia 'risco ligado' sem distinguir 'o filtro correu e aprovou' de 'o
    filtro nao chegou a correr'. Quem le tem direito a saber qual dos dois foi.
    """
    return len(closes) >= config.SMA_REGIME_DAYS


def equity_regime(benchmark_closes: list[float]) -> str:
    avg = sma(benchmark_closes, config.SMA_REGIME_DAYS)
    if avg is None or benchmark_closes[-1] >= avg:
        return "risk_on"
    return "risk_off"


def allocate(ranked: list[tuple[str, float]], exposure: float, top_n: int,
             min_positions: int, max_weight: float) -> tuple[dict[str, float], str]:
    """Distribui `exposure` pelos melhores candidatos com teto e piso.

    Devolve (pesos, nota). Se os candidatos elegiveis nao chegarem ao piso de
    diversificacao, devolve carteira vazia — o resto fica em caixa.
    """
    if len(ranked) < min_positions:
        return {}, (f"piso de diversificacao nao atingido "
                    f"({len(ranked)} < {min_positions}) -> 100% caixa")
    chosen = ranked[:top_n]
    weight = min(exposure / len(chosen), max_weight)
    weights = {symbol: weight for symbol, _ in chosen}
    allocated = weight * len(chosen)
    note = ""
    if allocated < exposure - 1e-9:
        note = (f"teto de {max_weight*100:.0f}% por posicao deixou "
                f"{(exposure - allocated)*100:.1f}% em caixa")
    return weights, note


def _screen(universe: dict[str, Series], benchmark_score: float | None,
            min_turnover: float, score_fn) -> tuple[list[tuple[str, float]],
                                                     list[dict]]:
    """Aplica liquidez + historico + forca relativa. Devolve (ranked, rejeitados)."""
    ranked: list[tuple[str, float]] = []
    rejected: list[dict] = []
    for symbol, series in sorted(universe.items()):
        closes = [close for _, close, _ in series]
        score = score_fn(closes)
        if score is None:
            rejected.append({"symbol": symbol, "reason": "historico insuficiente"})
            continue
        turnover = median_turnover(series, config.LIQUIDITY_WINDOW_DAYS)
        if turnover < min_turnover:
            rejected.append({"symbol": symbol,
                             "reason": f"liquidez baixa ({turnover/1e6:.1f}M "
                                       f"< {min_turnover/1e6:.0f}M)"})
            continue
        if benchmark_score is not None and score <= benchmark_score:
            rejected.append({"symbol": symbol,
                             "reason": f"nao bate o benchmark "
                                       f"({score*100:+.1f}% <= {benchmark_score*100:+.1f}%)"})
            continue
        ranked.append((symbol, score))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked, rejected


def equity_decision(universe: dict[str, Series],
                    benchmark_closes: list[float]) -> dict:
    """Decisao da carteira de acoes EUA (benchmark SPY)."""
    regime = equity_regime(benchmark_closes)
    exposure = 1.0 if regime == "risk_on" else config.EQUITY_RISK_OFF_EXPOSURE
    benchmark_score = equity_momentum_score(benchmark_closes)

    ranked, rejected = _screen(universe, benchmark_score,
                               config.MIN_MEDIAN_TURNOVER_USD,
                               equity_momentum_score)
    weights, note = allocate(ranked, exposure, config.EQUITY_TOP_N,
                             config.EQUITY_MIN_POSITIONS,
                             config.MAX_ACTIVE_POSITION_WEIGHT)
    return _decision(weights, regime, benchmark_score, ranked, rejected, note,
                     hurdle="SPY",
                     regime_avaliado=regime_avaliavel(benchmark_closes))


def b3_decision(universe: dict[str, Series], benchmark_closes: list[float],
                cdi_window_return: float | None) -> dict:
    """Decisao da carteira B3. O obstaculo e o MAIOR entre Ibovespa e CDI."""
    regime = equity_regime(benchmark_closes)
    exposure = 1.0 if regime == "risk_on" else config.B3_RISK_OFF_EXPOSURE
    ibov_score = equity_momentum_score(benchmark_closes)

    hurdle_name = "IBOV"
    hurdle = ibov_score
    if cdi_window_return is not None:
        if hurdle is None or cdi_window_return > hurdle:
            hurdle, hurdle_name = cdi_window_return, "CDI"

    ranked, rejected = _screen(universe, hurdle,
                               config.MIN_MEDIAN_TURNOVER_BRL,
                               equity_momentum_score)
    weights, note = allocate(ranked, exposure, config.B3_TOP_N,
                             config.B3_MIN_POSITIONS,
                             config.MAX_ACTIVE_POSITION_WEIGHT)
    return _decision(weights, regime, hurdle, ranked, rejected, note,
                     hurdle=hurdle_name,
                     regime_avaliado=regime_avaliavel(benchmark_closes))


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


def crypto_decision(universe: dict[str, Series]) -> dict:
    """Decisao da carteira crypto: BTC como ancora + alts que batem o BTC.

    BTC nao e posicao ativa (e o proprio benchmark), por isso tem teto proprio;
    as altcoins sao as apostas ativas e respeitam o teto da secao 4.
    """
    btc_series = universe.get("BTC", [])
    btc_closes = [close for _, close, _ in btc_series]
    regime = crypto_regime(btc_closes)
    exposure = 1.0 if regime == "risk_on" else config.CRYPTO_RISK_OFF_EXPOSURE
    btc_score = crypto_momentum_score(btc_closes)

    if btc_score is None:
        weights = {"BTC": min(exposure, config.CRYPTO_BTC_ANCHOR_MAX)}
        return _decision(weights, regime, None, [], [],
                         "sem historico do BTC: so ancora", hurdle="BTC",
                         regime_avaliado=regime_avaliavel(btc_closes))

    alts = {s: series for s, series in universe.items() if s != "BTC"}
    # As duas fontes ja reportam volume em unidades da moeda base (a CoinGecko
    # e normalizada na leitura), por isso preco x volume e giro em USD em ambas
    # e o limiar significa a mesma coisa venha de onde vier.
    ranked, rejected = _screen(alts, btc_score,
                               config.MIN_MEDIAN_TURNOVER_CRYPTO_USD,
                               crypto_momentum_score)

    btc_weight = min(exposure * config.CRYPTO_BTC_CORE_WEIGHT,
                     config.CRYPTO_BTC_ANCHOR_MAX)
    note = ""
    weights: dict[str, float] = {}
    if ranked:
        chosen = ranked[: config.CRYPTO_MAX_ALTS]
        alt_budget = exposure * (1.0 - config.CRYPTO_BTC_CORE_WEIGHT)
        per_alt = min(alt_budget / len(chosen), config.MAX_ACTIVE_POSITION_WEIGHT)
        weights = {symbol: per_alt for symbol, _ in chosen}
        if per_alt * len(chosen) < alt_budget - 1e-9:
            note = (f"teto de {config.MAX_ACTIVE_POSITION_WEIGHT*100:.0f}% por alt "
                    f"deixou {(alt_budget - per_alt*len(chosen))*100:.1f}% em caixa")
        weights["BTC"] = btc_weight
    else:
        # nenhuma alt bate o BTC: a ancora absorve a exposicao permitida
        weights["BTC"] = min(exposure, config.CRYPTO_BTC_ANCHOR_MAX)
        note = "nenhuma alt bate o BTC: so ancora"
    return _decision(weights, regime, btc_score, ranked, rejected, note,
                     hurdle="BTC",
                     regime_avaliado=regime_avaliavel(btc_closes))


def _decision(weights: dict[str, float], regime: str, hurdle_score: float | None,
              ranked: list[tuple[str, float]], rejected: list[dict],
              note: str, hurdle: str, regime_avaliado: bool = True) -> dict:
    scores = dict(ranked)
    return {
        "weights": weights,
        "regime": regime,
        "regime_avaliado": regime_avaliado,
        "hurdle": hurdle,
        "hurdle_score": hurdle_score,
        "eligible_count": len(ranked),
        "selected": [{"symbol": s, "score": round(scores.get(s, 0.0), 4),
                      "weight": round(w, 4)}
                     for s, w in sorted(weights.items(),
                                        key=lambda kv: -kv[1])],
        "rejected": rejected,
        "note": note,
        "cash_weight": round(max(0.0, 1.0 - sum(weights.values())), 4),
    }
