"""Nucleo compartilhado do teste transversal do escore Delta.

PESQUISA APENAS. Nada aqui le ou escreve ledger, toca parametro congelado ou
realimenta qualquer motor. O escore e replica verbatim da formula congelada em
tools/gate_btc_delta_v12_engine.py, linhas 265-332:

    score = 0.20*z(ret7) + 0.35*z(ret14) + 0.35*z(ret30)
            - 0.10*z(vol30) + 0.05*z(log1p(mediana do volume USD de 14d))

com z = z-score transversal do dia (desvio POPULACIONAL, ddof=0) e
vol30 = desvio AMOSTRAL (ddof=1) dos ultimos 30 retornos diarios. Um componente
faltante torna o escore indefinido, como o NaN faz no script canonico — um
escore parcial nao e um sinal mais fraco, e uma formula diferente.
"""
from __future__ import annotations

import json
import math
import os
import statistics as st
from collections import defaultdict

MIN_HISTORY = 30          # igual a minimum_signal_history do motor
MIN_NAMES_PER_DAY = 20    # corte transversal fino demais nao e corte transversal


def data_dir(explicit: str | None = None) -> str:
    """Diretorio com os .json por simbolo. Ordem: argumento, env, ./data."""
    return (explicit
            or os.environ.get("DELTA_XS_DATA")
            or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))


# ----------------------------------------------------------------- carregamento
def load(path: str | None = None) -> dict[str, dict[str, dict]]:
    """date -> base -> barra. Cada arquivo e <INST>-USDT-SWAP.json."""
    d = data_dir(path)
    if not os.path.isdir(d):
        raise SystemExit(f"diretorio de dados nao encontrado: {d}\n"
                         f"rode fetch_okx.py primeiro, ou aponte DELTA_XS_DATA.")
    panel: dict[str, dict[str, dict]] = defaultdict(dict)
    for fn in sorted(os.listdir(d)):
        # "_" prefixa metadados do coletor (_universe.json), que nao sao painel
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        stem = fn[:-5]
        # OKX vem como "BTC-USDT-SWAP"; Binance Vision como "BTCUSDT"
        base = (stem.split("-")[0] if "-" in stem
                else (stem[:-4] if stem.endswith("USDT") else stem)).upper()
        for r in json.load(open(os.path.join(d, fn))):
            if r.get("close") and r["close"] > 0:
                panel[r["date"]][base] = r
    if not panel:
        raise SystemExit(f"nenhum dado em {d}")
    return panel


# ------------------------------------------------------------------- estatistica
def pstdev(v):
    return st.pstdev(v) if v else None


def sstdev(v):
    return st.stdev(v) if len(v) > 1 else None


def zrow(vals: dict):
    """z-score transversal. Cross-section plano devolve None, como no motor:
    uma secao sem dispersao nao carrega informacao de ranking."""
    present = [v for v in vals.values() if v is not None]
    if not present:
        return {k: None for k in vals}
    mu, sd = st.fmean(present), pstdev(present)
    if not sd:
        return {k: None for k in vals}
    return {k: (None if v is None else (v - mu) / sd) for k, v in vals.items()}


# --------------------------------------------------------------------- construcao
def build(panel):
    """Devolve (dates, bases, close, score, ret1)."""
    dates = sorted(panel)
    idx = {d: i for i, d in enumerate(dates)}
    bases = sorted({b for d in dates for b in panel[d]})
    close = {d: {b: panel[d].get(b, {}).get("close") for b in bases} for d in dates}
    vol = {d: {b: panel[d].get(b, {}).get("volume_usd") for b in bases} for d in dates}

    def sret(day, base, lag):
        i = idx[day]
        if i < lag:
            return None
        past, now = close[dates[i - lag]][base], close[day][base]
        if past is None or now is None or past <= 0:
            return None
        return now / past - 1

    ret1 = {d: {b: sret(d, b, 1) for b in bases} for d in dates}

    score = {}
    for d in dates:
        i = idx[d]
        v30, liq = {}, {}
        for b in bases:
            w = [ret1[dates[j]][b] for j in range(max(0, i - 29), i + 1)]
            c = [x for x in w if x is not None]
            v30[b] = sstdev(c) if len(c) >= MIN_HISTORY else None
            vw = [vol[dates[j]][b] for j in range(max(0, i - 13), i + 1)]
            vc = [x for x in vw if x is not None]
            liq[b] = math.log1p(st.median(vc)) if len(vc) >= 7 else None
        z7 = zrow({b: sret(d, b, 7) for b in bases})
        z14 = zrow({b: sret(d, b, 14) for b in bases})
        z30 = zrow({b: sret(d, b, 30) for b in bases})
        zv, zl = zrow(v30), zrow(liq)
        row = {}
        for b in bases:
            p = (z7[b], z14[b], z30[b], zv[b], zl[b])
            row[b] = None if any(x is None for x in p) else (
                0.20 * p[0] + 0.35 * p[1] + 0.35 * p[2] - 0.10 * p[3] + 0.05 * p[4])
        score[d] = row
    return dates, bases, close, score, ret1


def usd_volume(panel, dates, bases):
    return {d: {b: panel[d].get(b, {}).get("volume_usd") for b in bases} for d in dates}


# ------------------------------------------------------------------ Fama-MacBeth
def _ranks(v):
    """Postos medios, com empates compartilhando o posto medio."""
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def fama_macbeth(dates, bases, score, ret1, keep=None, min_names=MIN_NAMES_PER_DAY,
                 winsor=None, rank=False):
    """Inclinacao transversal por dia do escore(t) contra o retorno(t+1).

    O retorno e DEMEANADO dentro do dia, o que torna o teste neutro a mercado
    por construcao: mede o sinal, nao a direcao do BTC. Testar a media das
    inclinacoes no tempo trata a correlacao transversal do dia corretamente.

    winsor: limite absoluto de retorno diario (ex. 0.50 = +-50%). Minimos
        quadrados sao dominados por caudas: num painel que inclui micro-caps,
        um unico retorno de +13.254% num dia reescreve a inclinacao daquele dia
        e, por tabela, a media da serie. Winsorizar apara isso SEM descartar a
        observacao, que continua contando como "subiu muito".
    rank: se True, usa postos em vez de niveis (equivalente a Spearman). Nao tem
        unidade economica, mas e imune a outlier: responde so "o escore ordena
        o retorno do dia seguinte?".
    """
    out = []
    for i, d in enumerate(dates[:-1]):
        nxt = dates[i + 1]
        pr = [(b, score[d][b], ret1[nxt][b]) for b in bases
              if score[d].get(b) is not None and ret1[nxt].get(b) is not None]
        if keep:
            pr = [p for p in pr if keep(d, p[0])]
        if len(pr) < min_names:
            continue
        xs = [p[1] for p in pr]
        ys = [p[2] for p in pr]
        if winsor is not None:
            ys = [max(-winsor, min(winsor, y)) for y in ys]
        if rank:
            xs, ys = _ranks(xs), _ranks(ys)
        my = st.fmean(ys)
        ys = [y - my for y in ys]
        mx = st.fmean(xs)
        den = sum((x - mx) ** 2 for x in xs)
        if den == 0:
            continue
        out.append((d, sum((x - mx) * y for x, y in zip(xs, ys)) / den, len(pr)))
    return out


def tstat(values):
    """(media, t). t = media / erro-padrao da media."""
    if len(values) < 2:
        return float("nan"), float("nan")
    m = st.fmean(values)
    se = st.stdev(values) / math.sqrt(len(values))
    return m, (m / se if se else float("nan"))


def decile_spread(dates, bases, score, ret1, min_names=MIN_NAMES_PER_DAY):
    """Decil alto menos decil baixo, demeanado no dia."""
    out = []
    for i, d in enumerate(dates[:-1]):
        nxt = dates[i + 1]
        pr = [(score[d][b], ret1[nxt][b]) for b in bases
              if score[d].get(b) is not None and ret1[nxt].get(b) is not None]
        if len(pr) < min_names:
            continue
        my = st.fmean([p[1] for p in pr])
        pr = [(s, r - my) for s, r in pr]
        pr.sort(key=lambda p: p[0])
        k = max(1, len(pr) // 10)
        out.append((d, st.fmean([r for _, r in pr[-k:]]) - st.fmean([r for _, r in pr[:k]])))
    return out


def pit_rank(dates, bases, vol, lookback=30, min_obs=15):
    """Ranking de liquidez PONTO-NO-TEMPO: volume mediano ate aquele dia.

    Usar o ranking de hoje para tras seria selecionar o universo com hindsight.
    """
    idx = {d: i for i, d in enumerate(dates)}
    out = {}
    for d in dates:
        i = idx[d]
        vals = {}
        for b in bases:
            w = [vol[dates[j]][b] for j in range(max(0, i - lookback + 1), i + 1)]
            c = [x for x in w if x is not None]
            if len(c) >= min_obs:
                vals[b] = st.median(c)
        out[d] = {b: r for r, b in enumerate(sorted(vals, key=lambda k: -vals[k]))}
    return out
