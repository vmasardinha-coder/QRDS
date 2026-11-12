#!/usr/bin/env python3
"""Checagem de saude do pipeline que alimenta os ledgers Delta.

Existe porque em 2026-11-08 uma run ficou VERMELHA, ninguem viu, e o V11 travou
em 86 observacoes por dias com todo o resto reportando verde. A entrega diaria
lia apenas os ledgers Delta e nao enxergava a cadeia que os alimenta.

ENCERRAMENTO DO V11, decidido pelo dono do repositorio em 2026-11-12. O vao de
8 a 11 de novembro foi ACEITO. O V11 fica em 86 observacoes com data_as_of
2026-11-07, pelos mesmos motivos registrados para o V12: os dias faltantes nunca
foram observados e a unica via de fabrica-los -- re-coletar com cutoff fixado --
usaria o universo point-in-time de hoje, que e o vies que destruiu o portao da
V14. A tentativa de recuperar pelo passo 17 do workflow foi feita e barrada por
uma guarda correta ("Gateway source close moved backwards"): o gateway_dynamics
ja estava quatro dias a frente do artefato que o replay traria, e gravar aquele
close andaria para tras num ledger append-only.

Consequencia disso, que este script passa a afirmar em vez de alarmar: o monitor
exige exatamente a proxima data (ultima do ledger + 1 dia) e levanta MonitorError
se o cutoff for posterior. Com o ledger parado em 2026-11-07, NENHUM cutoff
futuro serve. O V11 nao volta a andar, e isso e o esperado, nao uma falha.

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

# Estado congelado das series encerradas. Mudanca em qualquer um e anomalia grave.
ENCERRADAS = {
    "delta_paper_monitor": ("2026-11-07", 86, "V11", "vao de 8-11 nov aceito em 2026-11-12"),
    "delta_v12_engine": ("2026-09-19", 12, "V12", "lacuna de 20-21 set, encerrada em 2026-09-22"),
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

    # ---- V13: a unica serie que ainda conta, e ela nao depende do ponteiro ----
    raw = show("runtime/ledgers/delta_v13_engine/STATUS.json")
    if raw is None:
        problemas.append("V13: ledger ilegivel no branch runtime")
    else:
        d = json.loads(raw)
        asof, obs = iso(d["data_as_of"]), d.get("observed_days")
        linhas.append(f"V13        : {asof}, {obs} de 60")
        atraso = (date.today() - timedelta(days=1) - asof).days
        if atraso >= 2:
            problemas.append(
                f"V13 ATRASADO: data_as_of {asof}, e o ultimo fechamento UTC completo "
                f"e {date.today() - timedelta(days=1)} -- {atraso} dias de atraso. "
                f"Esta e a unica serie que ainda conta; se ela parar, para tudo. "
                f"O motor dela roda encadeado na pinagem de precos, nao por "
                f"agendamento, entao atraso de algumas horas e normal e dois dias nao.")
        if d.get("promotion_allowed") is not False:
            problemas.append(f"V13 promotion_allowed={d.get('promotion_allowed')}, tem de ser false")

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
                f"             -> cadeia de handoff PARADA (o sidecar exige cutoff "
                f"{lock + timedelta(days=1)}, a coleta resolve {hoje_cutoff}). "
                f"Conhecido e aceito: nao bloqueia mais nenhuma serie que conte, "
                f"porque o V11 esta encerrado e o V13 nao depende do ponteiro. "
                f"O lock25_50 tambem para de avancar enquanto isso durar.")
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
        print("   Sem problema. V13 andando, series encerradas intocadas, sem recusa no V2A.")
    print()
    print("   O que este script NAO ve (precisa da API do GitHub):")
    print("   - runs de gate-btc-delta-v13-engine.yml que falharam;")
    print("   - passos 'skipped' por continue-on-error em qualquer workflow.")
    print("   Regra: conclusion mente quando ha continue-on-error; vale o outcome.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
