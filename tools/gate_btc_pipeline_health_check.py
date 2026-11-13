#!/usr/bin/env python3
"""Checagem de saude do pipeline que alimenta os ledgers Delta.

Existe porque em 2026-11-08 uma run ficou VERMELHA, ninguem viu, e o V11 travou
em 86 observacoes por dias com todo o resto reportando verde. A entrega diaria
lia apenas os ledgers Delta e nao enxergava a cadeia que os alimenta.

CORRECAO DE 2026-11-13. Em 2026-11-12 este script deu o V11 como ENCERRADO em 86
observacoes, com o vao de 8 a 11 de novembro aceito. ISSO ESTAVA ERRADO, e o
proprio ledger provou: em 13/11 ele esta em 91 observacoes, data_as_of
2026-11-12, com os cinco dias contabilizados.

O erro foi de diagnostico, meu. Eu conclui que os dias do V11 eram irrecuperaveis
porque o manifesto de handoff daqueles dias nunca existiu. O monitor NAO precisa
do manifesto de handoff: ele precisa do zip de fonte do Delta, que existe dentro
do artefato de coleta de cada dia, e esses artefatos existiram o tempo todo, um
por dia. O ponteiro travado nunca significou que o dado tinha sumido -- ele so
dizia qual run ler. A recuperacao veio por um caminho de fonte isolada que
alimenta o monitor direto do artefato de cada dia.

E a recuperacao e LEGITIMA, verificada linha a linha: cada um dos cinco dias
carrega um source_run_id diferente, e cada run foi a coleta da manha seguinte
aquele dia, com o cutoff natural -- 08/11 veio da run de 09/11, 09/11 da run de
10/11, e assim por diante. Nenhum dia foi re-coletado com cutoff fixado, entao o
vies de universo point-in-time que destruiu o portao da V14 nao ocorreu.

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

# Estado congelado das series encerradas. Mudanca e anomalia grave.
# O V11 NAO esta aqui: ele voltou a andar em 2026-11-12 e segue vivo.
ENCERRADAS = {
    "delta_v12_engine": ("2026-09-19", 12, "V12", "lacuna de 20-21 set, encerrada em 2026-09-22"),
}

# Series vivas: nome do ledger -> (rotulo, limiar do contrato ou None).
VIVAS = {
    "delta_paper_monitor": ("V11", None),   # sem limiar: o contrato nao define um
    "delta_v13_engine": ("V13", 60),
}


def show(path: str) -> str | None:
    r = subprocess.run(["git", "-C", REPO, "show", f"{BRANCH}:{path}"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def tree(path: str) -> list[str]:
    r = subprocess.run(["git", "-C", REPO, "ls-tree", "-r", "--name-only", BRANCH, path],
                       capture_output=True, text=True)
    return sorted(x.rsplit("/", 1)[-1][:-5] for x in r.stdout.split() if x.endswith(".json"))


def iso(value: str) -> date:
    return date.fromisoformat(str(value)[:10])


def main() -> int:
    problemas: list[str] = []
    linhas: list[str] = []

    # ---- series encerradas: so confirmamos que nao se moveram ----
    for ledger, (asof, obs, nome, motivo) in ENCERRADAS.items():
        raw = show(f"runtime/ledgers/{ledger}/STATUS.json")
        if raw is None:
            problemas.append(f"{nome}: ledger ilegivel no branch runtime")
            continue
        d = json.loads(raw)
        if str(d.get("data_as_of")) != asof or d.get("observed_days") != obs:
            problemas.append(
                f"ANOMALIA GRAVE: o ledger do {nome} MUDOU -- data_as_of "
                f"{d.get('data_as_of')}, observed_days {d.get('observed_days')}. "
                f"Ele esta ENCERRADO e deve permanecer em {asof} com {obs}. "
                f"Um ledger encerrado que anda significa que algo escreveu nele.")
        else:
            linhas.append(f"{nome:10} : {asof}, {obs} observacoes, ENCERRADA ({motivo})")

    # ---- series vivas: atraso e governanca ----
    for ledger, (nome, limiar) in VIVAS.items():
        raw = show(f"runtime/ledgers/{ledger}/STATUS.json")
        if raw is None:
            problemas.append(f"{nome}: ledger ilegivel no branch runtime")
            continue
        d = json.loads(raw)
        asof, obs = iso(d["data_as_of"]), d.get("observed_days")
        conta = f"{obs} de {limiar}" if limiar else f"{obs} observacoes (sem limiar no contrato)"
        linhas.append(f"{nome:10} : {asof}, {conta}")
        atraso = (date.today() - timedelta(days=1) - asof).days
        if atraso >= 2:
            problemas.append(
                f"{nome} ATRASADO: data_as_of {asof}, e o ultimo fechamento UTC completo "
                f"e {date.today() - timedelta(days=1)} -- {atraso} dias de atraso. "
                f"Atraso de horas e normal e nao e lacuna; dois dias ou mais nao e. "
                f"Antes de concluir que parou, confira se a cadeia que alimenta este "
                f"ledger rodou -- em 2026-11-08 ela parou por quatro dias com tudo verde.")
        if d.get("promotion_allowed") is not False:
            problemas.append(f"{nome} promotion_allowed={d.get('promotion_allowed')}, tem de ser false")

    # ---- recusas do ledger de qualidade do V2A ----
    # Desde 2026-11-11 uma contagem incoerente do coletor nao derruba mais o job:
    # o dia nao e gravado, a recusa vai para refusals/ e a run fecha VERDE. Como
    # ela saiu do semaforo, este e o unico lugar onde aparece.
    refusals = tree("runtime/data_quality/v2a/refusals/")
    if refusals:
        problemas.append(
            f"DIA RECUSADO PELO LEDGER DE QUALIDADE DO V2A: {len(refusals)} no total, a mais "
            f"recente {refusals[-1]}. O dia NAO foi gravado e a guarda nao foi afrouxada, mas "
            f"a run fecha verde nesse caso, entao este e o unico alarme. Leia "
            f"runtime/data_quality/v2a/refusals/{refusals[-1]}.json e investigue o manifesto "
            f"do coletor V2A, nao a guarda.")
    else:
        linhas.append("recusas V2A: nenhuma")

    # ---- a cadeia de handoff: informativa agora, porque o V11 esta encerrado ----
    ptr_raw = show("runtime/GATE_BTC_LATEST_ELIGIBLE_RUN.json")
    locks = tree("runtime/ledgers/lock25_50/snapshots/")
    if ptr_raw and locks:
        cutoff = iso(json.loads(ptr_raw)["data_cutoff"])
        lock = iso(locks[-1])
        hoje_cutoff = date.today() - timedelta(days=1)
        linhas.append(f"ponteiro   : cutoff {cutoff}   lock25_50: {lock}")
        if lock + timedelta(days=1) != hoje_cutoff:
            linhas.append(
                f"             -> cadeia de handoff do LOCK PARADA (o sidecar exige cutoff "
                f"{lock + timedelta(days=1)}, a coleta resolve {hoje_cutoff}), e o "
                f"lock25_50 nao avanca enquanto isso durar. NAO bloqueia o V11 nem o "
                f"V13: desde 2026-11-12 o V11 e alimentado pelo caminho de fonte "
                f"isolada, direto do artefato de cada dia, e o V13 nunca dependeu do "
                f"ponteiro. Ponteiro parado deixou de ser sintoma de serie parada.")
        else:
            linhas.append("             -> cadeia de handoff saudavel")

    print("=" * 72)
    print("SAUDE DO PIPELINE")
    print("=" * 72)
    for l in linhas:
        print("  " + l)
    print()
    if problemas:
        print(f"!! {len(problemas)} PROBLEMA(S) -- destaque da entrega, acima das cotas:")
        for p in problemas:
            print()
            for i, seg in enumerate(p.split(". ")):
                print(("   - " if i == 0 else "     ") + seg.strip() + ("." if not seg.endswith(".") else ""))
    else:
        print("   Sem problema. Series vivas em dia, V12 intocado, sem recusa no V2A.")
    print()
    print("   O que este script NAO ve (precisa da API do GitHub):")
    print("   - runs de gate-btc-delta-v13-engine.yml e gate-btc-delta-paper-monitor.yml")
    print("     que falharam -- lembrando que o job upstream-daily-delivery da um")
    print("     falso vermelho quando um job IRMAO da coleta falha com outro dataset;")
    print("   - passos 'skipped' por continue-on-error em qualquer workflow.")
    print("   Regra: conclusion mente quando ha continue-on-error; vale o outcome.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
