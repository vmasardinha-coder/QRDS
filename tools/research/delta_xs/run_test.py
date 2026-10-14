"""Teste transversal principal + robustez + vies, num comando so.

PESQUISA APENAS. Nao le nem escreve ledger, nao toca parametro congelado,
nao realimenta motor nenhum. O resultado daqui NAO se aplica ao V11 nem ao
V13, que ja tem retorno observado: aplicar um teste desenhado depois de ver
a curva deles seria retune.

Uso:
    python3 -I run_test.py
    python3 -I run_test.py --data /caminho --out resultados/
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import statistics as st
import sys
from collections import defaultdict

# python3 -I (recomendado, porque o diretorio de dados e conteudo baixado) tira
# o diretorio do script do sys.path; recolocamos so ele, nunca o cwd.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xs_core as X  # noqa: E402


def line(lbl, lam):
    v = [l for _, l, _ in lam] if lam and len(lam[0]) == 3 else lam
    m, t = X.tstat(v)
    print(f"  {lbl:<34} lambda={m:+.6f}  t={t:+.2f}  n={len(v)}")
    return m, t, len(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    panel = X.load(a.data)
    dates, bases, close, score, ret1 = X.build(panel)
    vol = X.usd_volume(panel, dates, bases)
    idx = {d: i for i, d in enumerate(dates)}

    print("=== PAINEL ===")
    print(f"  simbolos: {len(bases)}")
    print(f"  dias: {len(dates)}  {dates[0]} -> {dates[-1]}")

    lam = X.fama_macbeth(dates, bases, score, ret1)
    vals = [l for _, l, _ in lam]
    ns = [k for _, _, k in lam]
    m, t = X.tstat(vals)
    print()
    print("=== PRINCIPAL: Fama-MacBeth, escore(t) -> retorno demeanado(t+1) ===")
    print(f"  pares nome-dia: {sum(ns)}   dias: {len(vals)}   nomes/dia (mediana): "
          f"{int(st.median(ns))}")
    print(f"  lambda medio = {m:+.6f}  ({m*100:+.3f}% ao dia por desvio de escore)")
    print(f"  t = {t:+.2f}")
    print(f"  t por dia = {t/math.sqrt(len(vals)):.4f}  ->  para t=2,80 prospectivo "
          f"seriam {(2.80/t)**2*len(vals):,.0f} dias ({(2.80/t)**2*len(vals)/365:.1f} anos)")

    sp = X.decile_spread(dates, bases, score, ret1)
    sv = [s for _, s in sp]
    ms, ts = X.tstat(sv)
    vol_ann = st.stdev(sv) * math.sqrt(365)
    print()
    print("=== DECIL ALTO - DECIL BAIXO (demeanado no dia) ===")
    print(f"  spread medio = {ms*100:+.4f}%/dia   t = {ts:+.2f}")
    print(f"  anualizado {ms*365*100:+.1f}%   vol {vol_ann*100:.1f}%   "
          f"Sharpe {ms*365/vol_ann:.2f}   (BRUTO, sem custo)")

    print()
    print("=== POR ANO ===")
    byy = defaultdict(list)
    for d, l, _ in lam:
        byy[d[:4]].append(l)
    for y in sorted(byy):
        mm, tt = X.tstat(byy[y])
        print(f"  {y}  n={len(byy[y]):4d}  lambda={mm:+.6f}  t={tt:+.2f}")

    print()
    print("=== 1. CONCENTRACAO (a regra de reprovacao do contrato rascunho) ===")
    for k in (1, 5, 10, 25):
        v = sorted(vals)[:-k]
        mm, tt = X.tstat(v)
        print(f"  sem os {k:2d} melhores dias:            lambda={mm:+.6f}  t={tt:+.2f}")
    k2 = max(1, int(round(0.02 * len(vals))))
    _, t2 = X.tstat(sorted(vals)[:-k2])
    print(f"  --> regra do contrato: sem 2% dos dias ({k2}) t={t2:+.2f}; "
          f"reprova se < 1,80 -> {'REPROVA' if t2 < 1.80 else 'passa'}")

    print()
    print("=== 2. SUBPERIODOS ===")
    mid = dates[len(dates) // 2]
    line("1a metade", [x for x in lam if x[0] < mid])
    line("2a metade", [x for x in lam if x[0] >= mid])

    pit = X.pit_rank(dates, bases, vol)
    print()
    print("=== 3. UNIVERSO PONTO-NO-TEMPO (ranking de liquidez do proprio dia) ===")
    for N in (100, 60, 30):
        line(f"top {N} naquele dia",
             X.fama_macbeth(dates, bases, score, ret1,
                            keep=lambda d, b, N=N: pit[d].get(b, 10**9) < N))

    print()
    print("=== 4. LIMITE DO VIES DE SOBREVIVENCIA ===")
    print("  (a fonte purga deslistados; isto LIMITA o residuo, nao o elimina)")
    half = dates[len(dates) // 2]
    early, late = defaultdict(list), defaultdict(list)
    for d in dates:
        for b, r in pit[d].items():
            (early if d < half else late)[b].append(r)
    decl = {b for b in bases
            if len(early[b]) > 60 and len(late[b]) > 60
            and st.fmean(late[b]) > st.fmean(early[b]) + 5}
    print(f"  nomes que DECAIRAM no ranking: {len(decl)} de {len(bases)}")
    line("so os que decairam", X.fama_macbeth(dates, bases, score, ret1,
                                              keep=lambda d, b: b in decl))

    print()
    print("=== 5. INCUBACAO (descarta os primeiros dias pos-listagem) ===")
    first = {}
    for b in bases:
        ds = [d for d in dates if close[d][b] is not None]
        first[b] = ds[0] if ds else None
    for skip in (0, 90, 180):
        line(f"descartando {skip} dias",
             X.fama_macbeth(dates, bases, score, ret1,
                            keep=lambda d, b, s=skip: first[b] is not None
                            and idx[d] - idx[first[b]] >= s))

    print()
    print("=== 6. GIRO E CUSTO DO LIVRO DE DOIS DECIS ===")
    prev, turns, sizes = set(), [], []
    for i, d in enumerate(dates[:-1]):
        nxt = dates[i + 1]
        pr = [(score[d][b], b) for b in bases
              if score[d].get(b) is not None and ret1[nxt].get(b) is not None]
        if len(pr) < X.MIN_NAMES_PER_DAY:
            continue
        pr.sort()
        k = max(1, len(pr) // 10)
        cur = {b for _, b in pr[-k:]} | {b for _, b in pr[:k]}
        if prev and cur:
            turns.append(len(cur - prev) / len(cur))
        prev = cur
        sizes.append(2 * k)
    turn = st.fmean(turns)
    print(f"  livro medio {st.fmean(sizes):.1f} nomes   giro {turn*100:.1f}%/dia")
    print(f"  empate de custo: {ms/(2*turn)*10000:.0f} bps por perna "
          f"(corretagem e spread; NAO inclui impacto de mercado)")
    for bps in (3, 10, 30, 50):
        net = ms - 2 * turn * bps / 10000
        print(f"    {bps:3d} bps/perna -> {net*100:+.4f}%/dia  anual {net*365*100:+7.1f}%  "
              f"Sharpe {net*365/vol_ann:+.2f}")

    if a.out:
        os.makedirs(a.out, exist_ok=True)
        with open(os.path.join(a.out, "fama_macbeth_daily.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "lambda", "n_names"])
            w.writerows([[d, "%.8f" % l, k] for d, l, k in lam])
        with open(os.path.join(a.out, "decile_spread_daily.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "spread_demeaned"])
            w.writerows([[d, "%.8f" % s] for d, s in sp])
        print(f"\ngravado em {a.out}")


if __name__ == "__main__":
    main()
