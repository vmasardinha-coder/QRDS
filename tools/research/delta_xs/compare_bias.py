"""Mede o vies de sobrevivencia comparando duas fontes na MESMA janela.

PESQUISA APENAS. Nao le nem escreve ledger, nao toca parametro congelado, nao
realimenta motor nenhum, e NAO se aplica ao V11 nem ao V13.

A ideia e um controle simples. Duas fontes, mesmo periodo, mesmo escore, mesmo
teste; a unica coisa que muda e se os ativos mortos estao no painel:

  OKX        purga deslistados  -> painel so de sobreviventes
  CoinGecko  retem os mortos    -> painel com os que morreram

A diferenca entre os dois lambdas e a estimativa direta do vies que o teste de
2026-10-13 nao conseguiu eliminar.

LIMITE: as chaves demo da CoinGecko so servem 365 dias. Esta comparacao mede o
VIES, e nao avalia o portao historico do contrato V14, que exige min_days=1000
e t>=3.0 — em 365 dias o t esperado e da ordem de 1.4 mesmo que o efeito seja
real. Nao confunda um com o outro.

Uso:
    python3 -I compare_bias.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xs_core as X  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cg(path):
    """CoinGecko: date -> base -> barra, com market_cap para o ranking PIT."""
    panel = defaultdict(dict)
    mcap = defaultdict(dict)
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".json") or fn.startswith("_"):
            continue
        cid = fn[:-5]
        for r in json.load(open(os.path.join(path, fn))):
            if r.get("close") and r["close"] > 0:
                panel[r["date"]][cid] = r
                if r.get("market_cap"):
                    mcap[r["date"]][cid] = r["market_cap"]
    return panel, mcap


def report(tag, dates, bases, score, ret1, keep=None):
    lam = X.fama_macbeth(dates, bases, score, ret1, keep=keep)
    v = [l for _, l, _ in lam]
    ns = [k for _, _, k in lam]
    m, t = X.tstat(v)
    print(f"  {tag:<30} lambda={m:+.6f}  t={t:+.2f}  dias={len(v)}  "
          f"nomes/dia={int(st.median(ns)) if ns else 0}  pares={sum(ns)}")
    return m, t, len(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--okx", default=os.environ.get("DELTA_XS_DATA",
                                                    os.path.join(HERE, "data")))
    ap.add_argument("--cg", default=os.environ.get("DELTA_XS_CG_DATA",
                                                   os.path.join(HERE, "data_cg")))
    a = ap.parse_args()

    # ---------------- CoinGecko: retem mortos ----------------
    cg_panel, cg_mcap = load_cg(a.cg)
    cg_dates, cg_bases, cg_close, cg_score, cg_ret1 = X.build(cg_panel)
    print("=== PAINEL COINGECKO (retem ativos mortos) ===")
    print(f"  moedas: {len(cg_bases)}   dias: {len(cg_dates)}  "
          f"{cg_dates[0]} -> {cg_dates[-1]}")

    # ---------------- OKX: so sobreviventes, MESMA janela ----------------
    okx_panel_all = X.load(a.okx)
    lo, hi = cg_dates[0], cg_dates[-1]
    okx_panel = {d: v for d, v in okx_panel_all.items() if lo <= d <= hi}
    okx_dates, okx_bases, okx_close, okx_score, okx_ret1 = X.build(okx_panel)
    print("=== PAINEL OKX (so sobreviventes), mesma janela ===")
    print(f"  simbolos: {len(okx_bases)}   dias: {len(okx_dates)}  "
          f"{okx_dates[0]} -> {okx_dates[-1]}")

    print()
    print("=== COMPARACAO DIRETA — mesma janela, mesmo escore, mesmo teste ===")
    m_okx, t_okx, _ = report("OKX (sobreviventes)", okx_dates, okx_bases, okx_score, okx_ret1)
    m_cg, t_cg, _ = report("CoinGecko (com mortos)", cg_dates, cg_bases, cg_score, cg_ret1)
    if m_okx:
        print()
        print(f"  --> lambda CoinGecko / lambda OKX = {m_cg/m_okx:.2f}")
        print(f"      inflacao atribuivel a sobrevivencia: "
              f"{(1 - m_cg/m_okx)*100:+.0f}% do lambda da OKX")

    # ranking ponto-no-tempo por market cap, na fonte que retem mortos
    print()
    print("=== COINGECKO, universo ponto-no-tempo por market cap ===")
    rank = {}
    for d in cg_dates:
        order = sorted(cg_mcap.get(d, {}), key=lambda k: -cg_mcap[d][k])
        rank[d] = {b: i for i, b in enumerate(order)}
    for N in (200, 100, 50, 30):
        report(f"top {N} naquele dia", cg_dates, cg_bases, cg_score, cg_ret1,
               keep=lambda d, b, N=N: rank[d].get(b, 10**9) < N)

    # concentracao, a regra que reprova no contrato
    print()
    print("=== CONCENTRACAO na fonte limpa (regra do contrato: 2% dos dias) ===")
    lam = X.fama_macbeth(cg_dates, cg_bases, cg_score, cg_ret1)
    v = sorted(l for _, l, _ in lam)
    for frac in (0.01, 0.02, 0.05):
        k = max(1, int(round(frac * len(v))))
        mm, tt = X.tstat(v[:-k])
        flag = ""
        if abs(frac - 0.02) < 1e-9:
            flag = "   <-- regra do contrato: " + ("REPROVA" if tt < 1.80 else "passa")
        print(f"  sem {frac*100:.0f}% dos melhores dias ({k:2d}): "
              f"lambda={mm:+.6f}  t={tt:+.2f}{flag}")

    print()
    print("=== AVISO ===")
    print("  365 dias NAO satisfazem o portao historico do contrato V14")
    print("  (min_days=1000, required_t=3.0). Esta rodada mede o VIES, nao o portao.")
    n = len([1 for _ in lam])
    if n:
        _, t_all = X.tstat([l for _, l, _ in lam])
        print(f"  t observado aqui: {t_all:+.2f} em {n} dias. Para o mesmo efeito,")
        print(f"  1000 dias dariam t da ordem de {t_all*math.sqrt(1000/n):+.2f}.")


if __name__ == "__main__":
    main()
