#!/usr/bin/env python3
"""Checagem de saude do pipeline que alimenta os ledgers Delta.

Existe porque em 2026-11-08 uma run ficou VERMELHA, ninguem viu, e o V11 travou
em 86 observacoes por dias com todo o resto reportando verde. A entrega diaria
lia apenas os ledgers Delta e nao enxergava a cadeia que os alimenta.

Cobre as partes (a) e (b) do passo 2 da rotina, que saem do proprio branch
runtime e nao precisam da API do GitHub:

  (a) o ponteiro publicado (GATE_BTC_LATEST_ELIGIBLE_RUN.json) contra o
      data_as_of do ledger do V11 -- se o cutoff nao estiver a frente, o
      handoff esta quebrado e o V11 nao avanca, por mais verde que a coleta
      pareca;
  (b) o ultimo snapshot do lock25_50 -- o sidecar de valuacao exige
      cutoff == ultimo snapshot do lock + 1 dia (tools/
      gate_btc_lock_valuation_sidecar.py, _active_context). Se o lock atrasa,
      o sidecar recusa e, por rodar com continue-on-error, derruba o handoff
      em silencio.

As partes (c) e (d) -- runs vermelhas do Prospective Ledgers e passos skipped
do handoff na coleta -- precisam da API do GitHub e ficam fora deste script.

So leitura: nao escreve nada, nao toca ledger, nao faz rede.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta

BRANCH = "origin/gate-btc-runtime"
REPO = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                      capture_output=True, text=True).stdout.strip() or "."


def show(path: str) -> str | None:
    r = subprocess.run(["git", "-C", REPO, "show", f"{BRANCH}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def iso(value: str) -> date:
    return date.fromisoformat(str(value)[:10])


def main() -> int:
    problemas: list[str] = []
    linhas: list[str] = []

    v11_raw = show("runtime/ledgers/delta_paper_monitor/STATUS.json")
    ptr_raw = show("runtime/GATE_BTC_LATEST_ELIGIBLE_RUN.json")
    if v11_raw is None or ptr_raw is None:
        print("FALHA DE LEITURA: ledger do V11 ou ponteiro inacessivel no branch runtime")
        return 2

    v11 = json.loads(v11_raw)
    ptr = json.loads(ptr_raw)
    v11_asof = iso(v11["data_as_of"])
    v11_obs = v11.get("observed_days")
    cutoff = iso(ptr["data_cutoff"])

    linhas.append(f"V11        : data_as_of {v11_asof}  ({v11_obs} observacoes)")
    linhas.append(f"ponteiro   : data_cutoff {cutoff}  publicado {ptr.get('published_at_utc','?')[:19]}")
    linhas.append(f"             run_id {ptr.get('run_id','?')}")

    # (a) o ponteiro tem de estar a frente do ledger para haver o que contabilizar
    if cutoff <= v11_asof:
        problemas.append(
            f"HANDOFF QUEBRADO: o ponteiro esta em {cutoff} e o ledger do V11 em "
            f"{v11_asof}. Sem cutoff novo o monitor conclui UP_TO_DATE e NAO contabiliza "
            f"nada. O V11 nao avanca hoje, por mais verde que a coleta pareca.")
    else:
        linhas.append(f"             -> ponteiro a frente do ledger: ha fechamento a contabilizar")

    # regra de contiguidade do monitor: ele so aceita exatamente a proxima data.
    # Compara contra o ponteiro E contra o cutoff que a coleta de hoje resolveria,
    # porque o segundo e o que decide se o dia faltante ainda e alcancavel.
    esperado = v11_asof + timedelta(days=1)
    natural = date.today() - timedelta(days=1)
    if cutoff > esperado:
        problemas.append(
            f"V11 TRAVADO: o monitor exige exatamente {esperado} (ultima data do ledger "
            f"+ 1 dia) e levanta MonitorError se o cutoff for posterior. O ponteiro esta "
            f"em {cutoff}, adiante disso, entao ele vai recusar em vez de pular o dia.")
    if natural > esperado:
        problemas.append(
            f"DIA FALTANTE FORA DO ALCANCE DA ROTINA NORMAL: o V11 precisa de {esperado} "
            f"e a coleta agendada resolve {natural} (ultimo fechamento UTC completo). "
            f"Nenhuma execucao normal vai produzir {esperado}, entao o V11 fica parado "
            f"em {v11_obs} observacoes ate que aquele dia seja contabilizado a partir de "
            f"artefato congelado na epoca. Dias no vao: "
            f"{(natural - esperado).days + 1}. NAO re-coletar com cutoff fixado: isso "
            f"usaria o universo point-in-time de hoje, que e o vies que destruiu o portao "
            f"da V14.")

    # (b) o lock25_50 governa o sidecar, que governa o handoff
    r = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", BRANCH,
                        "runtime/ledgers/lock25_50/snapshots/"],
                       capture_output=True, text=True)
    snaps = sorted(x.rsplit("/", 1)[-1][:-5] for x in r.stdout.split() if x.endswith(".json"))
    if not snaps:
        problemas.append("lock25_50 sem snapshots legiveis no branch runtime")
    else:
        lock = iso(snaps[-1])
        linhas.append(f"lock25_50  : ultimo snapshot {lock}")
        prox = lock + timedelta(days=1)
        hoje_cutoff = date.today() - timedelta(days=1)
        if prox != hoje_cutoff:
            problemas.append(
                f"SIDECAR VAI RECUSAR: o lock25_50 esta em {lock}, entao o sidecar de "
                f"valuacao so aceita cutoff {prox}. A coleta de hoje resolve "
                f"{hoje_cutoff}. Ele vai levantar excecao e, por rodar com "
                f"continue-on-error, a run fecha VERDE enquanto handoff, delivery "
                f"request e ponteiro sao pulados.")
        else:
            linhas.append(f"             -> casa com o cutoff de hoje ({hoje_cutoff}): sidecar deve passar")

    v13_raw = show("runtime/ledgers/delta_v13_engine/STATUS.json")
    if v13_raw:
        v13 = json.loads(v13_raw)
        linhas.append(f"V13        : data_as_of {v13['data_as_of']}  ({v13.get('observed_days')} de 60)"
                      f"   [pipeline independente do ponteiro]")

    # Recusas do ledger de qualidade do V2A. Desde 2026-11-11 uma contagem
    # incoerente do coletor deixa de derrubar o job: o dia nao e gravado, a
    # recusa vai para refusals/ e a run fecha VERDE. Como ela saiu do semaforo,
    # tem de aparecer aqui -- e este e o unico lugar onde aparece.
    r = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", BRANCH,
                        "runtime/data_quality/v2a/refusals/"],
                       capture_output=True, text=True)
    refusals = sorted(x.rsplit("/", 1)[-1][:-5] for x in r.stdout.split() if x.endswith(".json"))
    if refusals:
        linhas.append(f"recusas V2A: {len(refusals)}, a ultima em {refusals[-1]}")
        problemas.append(
            f"DIA RECUSADO PELO LEDGER DE QUALIDADE DO V2A: {len(refusals)} no total, a mais "
            f"recente {refusals[-1]}. O dia NAO foi gravado e a guarda nao foi afrouxada, mas "
            f"a run fecha verde nesse caso, entao este e o unico alarme. Leia "
            f"runtime/data_quality/v2a/refusals/{refusals[-1]}.json e investigue o manifesto "
            f"do coletor V2A, nao a guarda.")
    else:
        linhas.append("recusas V2A: nenhuma")

    v12_raw = show("runtime/ledgers/delta_v12_engine/STATUS.json")
    if v12_raw:
        v12 = json.loads(v12_raw)
        if str(v12.get("data_as_of")) != "2026-09-19" or v12.get("observed_days") != 12:
            problemas.append(
                f"ANOMALIA GRAVE: o ledger do V12 mudou -- data_as_of "
                f"{v12.get('data_as_of')}, observed_days {v12.get('observed_days')}. "
                f"Ele esta ENCERRADO e deve permanecer em 2026-09-19 com 12.")
        else:
            linhas.append("V12        : 2026-09-19, 12 observacoes, intocado")

    print("=" * 72)
    print("SAUDE DO PIPELINE  (partes a e b do passo 2 da rotina)")
    print("=" * 72)
    for l in linhas:
        print("  " + l)
    print()
    if problemas:
        print(f"!! {len(problemas)} PROBLEMA(S) -- isto vira o destaque da entrega, acima das cotas:")
        for p in problemas:
            print()
            for i, seg in enumerate(p.split(". ")):
                print(("   - " if i == 0 else "     ") + seg.strip() + ("." if not seg.endswith(".") else ""))
    else:
        print("   Sem problema nas partes a e b.")
    print()
    print("   Ainda a checar pela API do GitHub (partes c e d):")
    print("   c) runs de gate-btc-prospective-ledgers.yml com conclusion failure,")
    print("      inclusive run_attempt > 1; sucesso em menos de 2 min e no-op.")
    print("   d) na ultima run de gate-btc-daily-research.yml, se os passos de")
    print("      handoff, delivery request e pointer estao 'skipped'.")
    print("   Regra: conclusion mente quando ha continue-on-error; vale o outcome.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
