"""GARCH(1,1) em Python puro para calibrar a volatilidade das opcoes.

Ajuste por maxima verosimilhanca gaussiana com variance targeting (omega
implicito na variancia amostral) e procura em grelha grossa+fina sobre
(alpha, beta). Sem dependencias externas; uma unica serie por dia torna o
custo irrelevante.

A previsao para o prazo da opcao usa o termo estrutural do GARCH:
E[sigma2_{t+h}] = lr + (alpha+beta)^(h-1) * (sigma2_{t+1} - lr),
com media sobre o horizonte e anualizacao por 252.
"""

from __future__ import annotations

import math

TRADING_DAYS_PER_YEAR = 252


def log_returns(closes: list[float]) -> list[float]:
    return [math.log(closes[i + 1] / closes[i]) for i in range(len(closes) - 1)]


def _neg_loglik(returns: list[float], omega: float, alpha: float,
                beta: float, var0: float) -> float:
    var = var0
    nll = 0.0
    for r in returns:
        var = omega + alpha * r * r + beta * var
        if var <= 0:
            return float("inf")
        nll += math.log(var) + r * r / var
    return nll


def fit_garch11(returns: list[float]) -> tuple[float, float, float]:
    """Devolve (omega, alpha, beta) por MLE com variance targeting."""
    n = len(returns)
    if n < 150:
        raise ValueError("historico insuficiente para GARCH")
    mean = sum(returns) / n
    rets = [r - mean for r in returns]
    sample_var = sum(r * r for r in rets) / (n - 1)
    if sample_var <= 0:
        raise ValueError("variancia amostral nula")

    def search(alphas: list[float], betas: list[float]) -> tuple[float, float, float]:
        best = (float("inf"), 0.05, 0.90)
        for a in alphas:
            for b in betas:
                if a + b >= 0.999:
                    continue
                omega = sample_var * (1.0 - a - b)
                nll = _neg_loglik(rets, omega, a, b, sample_var)
                if nll < best[0]:
                    best = (nll, a, b)
        return best

    coarse_a = [i / 100 for i in range(1, 26, 2)]      # 0.01..0.25
    coarse_b = [i / 100 for i in range(60, 99, 3)]     # 0.60..0.98
    _, a0, b0 = search(coarse_a, coarse_b)
    fine_a = [max(0.005, a0 + i / 200) for i in range(-3, 4)]
    fine_b = [min(0.995, max(0.30, b0 + i / 200)) for i in range(-3, 4)]
    _, a1, b1 = search(fine_a, fine_b)
    omega = sample_var * (1.0 - a1 - b1)
    return omega, a1, b1


def forecast_avg_vol(closes: list[float], horizon_trading_days: int) -> float:
    """Volatilidade anualizada prevista (media do horizonte) via GARCH(1,1)."""
    rets = log_returns(closes)
    omega, alpha, beta = fit_garch11(rets)
    persistence = alpha + beta
    long_run = omega / (1.0 - persistence)

    mean = sum(rets) / len(rets)
    rets = [r - mean for r in rets]
    var = sum(r * r for r in rets) / (len(rets) - 1)
    for r in rets:  # filtra a variancia condicional ate hoje
        var = omega + alpha * r * r + beta * var

    total = 0.0
    step = var  # E[sigma2_{t+1}] ja e o primeiro passo do filtro acima
    for _ in range(horizon_trading_days):
        total += step
        step = long_run + persistence * (step - long_run)
    avg_var = total / horizon_trading_days
    vol = math.sqrt(avg_var * TRADING_DAYS_PER_YEAR)
    if not (0.005 <= vol <= 3.0):
        raise ValueError(f"previsao GARCH implausivel: {vol:.3f}")
    return vol
