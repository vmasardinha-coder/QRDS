#!/usr/bin/env python3
"""Horizonte de previsao do escore congelado: rotacao diaria contra mais lenta.

PERGUNTA. O escore congelado prediz melhor o retorno de 1 dia, de 5 dias ou de
7 dias? Se o sinal for mais forte num horizonte longo, uma sucessora de rotacao
semanal tem base; se nao for, girar mais devagar so reduz custo e nao cria
retorno bruto nenhum.

METODO. Fama-MacBeth transversal, identico ao do portao da V14, com uma unica
diferenca: o retorno dependente e o de h dias a frente, nao o de 1 dia.

    escore(t)  ->  retorno(t -> t+h), demeanado DENTRO da data t

Demeanar dentro da data torna o teste neutro a mercado por construcao: mede
ordenacao transversal, nao direcao do BTC.

JANELAS NAO SOBREPOSTAS. Para h > 1, datas consecutivas compartilham dias de
retorno, o que autocorrelaciona as inclinacoes e INFLA o t. Por isso as datas
sao amostradas de h em h. Isso reduz n — e e exatamente o preco honesto de
medir horizonte longo. O deslocamento inicial (offset) varia de 0 a h-1 e os
h resultados sao reportados, porque escolher o melhor offset seria selecionar
o resultado depois de ve-lo.

ESCOPO. PESQUISA. Nenhum ledger lido ou escrito, nenhum parametro congelado
tocado, nenhuma ancora fixada. NAO aplicavel ao V11 nem ao V13, que ja tem
retorno observado: usar isto neles seria retune contra resultado conhecido.

Uso:
    python3 -I run_horizon.py
"""
import math
import os
import statistics as st
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xs_core as X

HORIZONS = (1, 3, 5, 7, 10, 14, 21)
WINSOR_PER_DAY = 0.50  # o mesmo limite do portao, escalado pelo horizonte


def forward_return(close, dates, idx, base, day, h):
    """Retorno composto de day ate day+h, ou None se faltar preco em qualquer ponta."""
    i = idx[day]
    if i + h >= len(dates):
        return None
    a = close[day][base]
    b = close[dates[i + h]][base]
    if a is None or b is None or a <= 0:
        return None
    return b / a - 1


def fm_horizon(dates, bases, score, close, idx, h, offset, winsor, rank=False):
    """Inclinacoes transversais em datas espacadas de h, comecando em offset."""
    out = []
    sample = [d for k, d in enumerate(dates) if k % h == offset % h]
    for d in sample:
        pr = []
        for b in bases:
            s = score[d].get(b)
            if s is None:
                continue
            r = forward_return(close, dates, idx, b, d, h)
            if r is None:
                continue
            pr.append((s, r))
        if len(pr) < X.MIN_NAMES_PER_DAY:
            continue
        xs = [p[0] for p in pr]
        ys = [p[1] for p in pr]
        if winsor is not None:
            ys = [max(-winsor, min(winsor, y)) for y in ys]
        if rank:
            xs, ys = X._ranks(xs), X._ranks(ys)
        my = st.fmean(ys)
        ys = [y - my for y in ys]
        mx = st.fmean(xs)
        den = sum((x - mx) ** 2 for x in xs)
        if den == 0:
            continue
        out.append(sum((x - mx) * y for x, y in zip(xs, ys)) / den)
    return out


def main():
    panel = X.load()
    dates, bases, close, score, ret1 = X.build(panel)
    idx = {d: i for i, d in enumerate(dates)}
    print("painel: %d simbolos, %d datas (%s a %s)"
          % (len(bases), len(dates), dates[0], dates[-1]))
    print("fonte: data.binance.vision — RETEM DESLISTADOS")
    print()
    print("Fama-MacBeth, retorno demeanado no dia, janelas NAO sobrepostas.")
    print("Winsor por horizonte = 50%% * sqrt(h). t de cada offset possivel.")
    print()
    hdr = "  h  |   n  |  lambda   |   t    | t por offset"
    print(hdr)
    print("-" * len(hdr))
    for h in HORIZONS:
        wins = WINSOR_PER_DAY * math.sqrt(h)
        ts, ns, lams = [], [], []
        for off in range(h):
            sl = fm_horizon(dates, bases, score, close, idx, h, off, wins)
            if len(sl) < 3:
                continue
            m, t = X.tstat(sl)
            ts.append(t)
            ns.append(len(sl))
            lams.append(m)
        if not ts:
            print(" %2d  |   -  |     -     |   -    | amostra insuficiente" % h)
            continue
        # o offset 0 e o reportado como principal; os outros medem a fragilidade
        print(" %2d  | %4d | %+.6f | %+5.2f  | %s"
              % (h, ns[0], lams[0], ts[0],
                 " ".join("%+.2f" % t for t in ts)))
    print()
    print("Mesma tabela em POSTOS (imune a outlier, sem unidade economica):")
    print(hdr)
    print("-" * len(hdr))
    for h in HORIZONS:
        ts, ns, lams = [], [], []
        for off in range(h):
            sl = fm_horizon(dates, bases, score, close, idx, h, off, None, rank=True)
            if len(sl) < 3:
                continue
            m, t = X.tstat(sl)
            ts.append(t)
            ns.append(len(sl))
            lams.append(m)
        if not ts:
            print(" %2d  |   -  |     -     |   -    | amostra insuficiente" % h)
            continue
        print(" %2d  | %4d | %+.6f | %+5.2f  | %s"
              % (h, ns[0], lams[0], ts[0], " ".join("%+.2f" % t for t in ts)))
    print()
    print("LEITURA. Um t que CRESCE com h diz que o sinal vive num horizonte")
    print("mais longo e que girar devagar o aproveita melhor. Um t que nao")
    print("cresce diz que rotacao lenta corta custo e nada mais — nao existe")
    print("retorno bruto adicional a capturar. O criterio do contrato da V14")
    print("exige t >= 3.0; nada aqui fixa ancora nem autoriza mexer em motor.")


if __name__ == "__main__":
    main()
