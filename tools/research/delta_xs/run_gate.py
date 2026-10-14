"""Avalia o portao historico do contrato V14 sobre painel SEM VIES DE SOBREVIVENCIA.

PESQUISA APENAS. Nao le nem escreve ledger de serie nenhuma, nao toca parametro
congelado, e NAO se aplica ao V11 nem ao V13.

Este e o unico script daqui que pode avaliar o portao, porque e o unico que roda
sobre uma fonte que retem deslistados em historico longo (data.binance.vision).
Os criterios NAO sao escolhidos aqui: sao lidos de
migration/reporting/delta_v14_engine_contract.json, que esta CONGELADO. Se um
criterio mudar, o contrato foi violado — o script confere o sha256 e avisa.

Uso:
    python3 -I run_gate.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xs_core as X  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT = os.path.normpath(os.path.join(
    HERE, "..", "..", "..", "migration", "reporting", "delta_v14_engine_contract.json"))
WINSOR = 0.50   # retornos diarios aparados a +-50%: ver compare_bias.py


def load_contract(path):
    c = json.load(open(path, encoding="utf-8"))
    body = dict(c)
    body["contract_sha256"] = None
    digest = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    ok = (digest == c.get("contract_sha256"))
    print(f"contrato: {os.path.basename(path)}")
    print(f"  freeze_date {c.get('freeze_date')}   anchor_date {c.get('anchor_date')}")
    print(f"  sha256 confere: {'SIM' if ok else 'NAO — CONTRATO ALTERADO APOS CONGELAR'}")
    if not ok:
        raise SystemExit("ABORTADO: o contrato nao bate com o proprio hash.")
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.environ.get(
        "DELTA_XS_BV_DATA", os.path.join(HERE, "data_bv")))
    ap.add_argument("--contract", default=CONTRACT)
    a = ap.parse_args()

    c = load_contract(a.contract)
    ht = c["evidence"]["historical_test"]
    uni = c["universe"]
    need_days = ht["min_days"]
    need_t = ht["required_t_statistic"]
    need_half = ht["required_t_each_half"]
    max_frac = ht["max_fraction_of_days_driving_result"]
    topn = uni["size"]
    print(f"  criterios: min_days={need_days}  t>={need_t}  cada metade>={need_half}  "
          f"concentracao: sem {max_frac*100:.0f}% dos dias t>={need_half}")
    print(f"  universo: top {topn} por liquidez ponto-no-tempo")

    panel = X.load(a.data)
    dates, bases, close, score, ret1 = X.build(panel)
    vol = X.usd_volume(panel, dates, bases)
    print()
    print("=== PAINEL (retem deslistados) ===")
    print(f"  simbolos ja listados: {len(bases)}   dias: {len(dates)}  "
          f"{dates[0]} -> {dates[-1]}")
    alive = defaultdict(int)
    for d in dates:
        for b in bases:
            if close[d][b] is not None:
                alive[b] += 1
    dead = [b for b in bases if close[dates[-1]][b] is None]
    print(f"  simbolos SEM barra no ultimo dia (deslistados/mortos): {len(dead)}")

    rank = X.pit_rank(dates, bases, vol,
                      lookback=uni["ranking_lookback_days"],
                      min_obs=uni["ranking_min_observations"])

    def gate_lam():
        return X.fama_macbeth(dates, bases, score, ret1, winsor=WINSOR,
                              keep=lambda d, b: rank[d].get(b, 10**9) < topn)

    lam = gate_lam()
    v = [l for _, l, _ in lam]
    ns = [k for _, _, k in lam]
    m, t = X.tstat(v)
    print()
    print(f"=== PORTAO HISTORICO — top {topn} ponto-no-tempo, winsorizado ===")
    print(f"  dias: {len(v)}   nomes/dia (mediana): {int(st.median(ns)) if ns else 0}   "
          f"pares nome-dia: {sum(ns)}")
    print(f"  lambda = {m:+.6f}   t = {t:+.2f}")

    mid = dates[len(dates) // 2]
    _, t1 = X.tstat([l for d, l, _ in lam if d < mid])
    _, t2 = X.tstat([l for d, l, _ in lam if d >= mid])
    k = max(1, int(round(max_frac * len(v))))
    _, tc = X.tstat(sorted(v)[:-k])

    checks = [
        (f"dias >= {need_days}", len(v) >= need_days, f"{len(v)}"),
        (f"t >= {need_t}", t >= need_t, f"{t:+.2f}"),
        (f"1a metade t >= {need_half}", t1 >= need_half, f"{t1:+.2f}"),
        (f"2a metade t >= {need_half}", t2 >= need_half, f"{t2:+.2f}"),
        (f"sem {max_frac*100:.0f}% dos dias ({k}) t >= {need_half}", tc >= need_half,
         f"{tc:+.2f}"),
    ]
    print()
    print("=== VEREDITO, criterio por criterio ===")
    for lbl, ok, val in checks:
        print(f"  [{'PASSA' if ok else 'FALHA'}] {lbl:<40} observado {val}")
    allok = all(ok for _, ok, _ in checks)
    print()
    print(f"  ==> PORTAO HISTORICO: {'APROVADO' if allok else 'REPROVADO'}")
    if not allok:
        print("      A hipotese nao sobreviveu ao proprio criterio preregistrado.")
        print("      Isto e um resultado, nao uma falha de execucao: o portao fez")
        print("      exatamente o que foi congelado para fazer.")
    print()
    print("  Em qualquer dos casos: promotion_allowed segue false, nenhuma ancora e")
    print("  fixada por este script, e nada aqui se aplica ao V11 ou ao V13.")

    print()
    print("=== CONTEXTO (descritivo, nao e criterio) ===")
    for N in (10, 30, 50, 100):
        lm = X.fama_macbeth(dates, bases, score, ret1, winsor=WINSOR,
                            keep=lambda d, b, N=N: rank[d].get(b, 10**9) < N)
        mm, tt = X.tstat([l for _, l, _ in lm])
        print(f"  top {N:3d} ponto-no-tempo: lambda={mm:+.6f}  t={tt:+.2f}  dias={len(lm)}")
    lm = X.fama_macbeth(dates, bases, score, ret1, winsor=WINSOR)
    mm, tt = X.tstat([l for _, l, _ in lm])
    print(f"  universo inteiro:      lambda={mm:+.6f}  t={tt:+.2f}  dias={len(lm)}")
    lm = X.fama_macbeth(dates, bases, score, ret1, rank=True,
                        keep=lambda d, b: rank[d].get(b, 10**9) < topn)
    _, tt = X.tstat([l for _, l, _ in lm])
    print(f"  top {topn} por postos (Spearman):          t={tt:+.2f}")


if __name__ == "__main__":
    main()
