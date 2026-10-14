"""Coletor de candles diarios de perpetuos USDT da OKX.

PESQUISA APENAS. Endpoints publicos de mercado, nenhuma credencial, nenhuma
ordem, nenhum endpoint privado. Nao escreve em runtime/ nem em ledger nenhum.

AVISO DE VIES, e e o limite serio desta fonte: a API da OKX PURGA instrumentos
deslistados. Verificado em 2026-10-14 — FTT-USDT-SWAP e SRM-USDT-SWAP, ambos
negociados no passado, retornam code 51001 "Instrument ID does not exist".
Um painel montado so com esta fonte contem APENAS SOBREVIVENTES, e isso empurra
qualquer resultado para cima. O vies nao e removivel por tratamento estatistico:
e ausencia de dado. Para um teste que valha como evidencia a fonte precisa reter
ativos mortos (ver migration/reporting/delta_v14_engine_contract_DRAFT.json).

Uso:
    python3 -I fetch_okx.py --top 140 --pages 20
    python3 -I fetch_okx.py --out /caminho/para/data
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time

TICKERS = "https://www.okx.com/api/v5/market/tickers?instType=SWAP"
CANDLES = "https://www.okx.com/api/v5/market/history-candles"


def get(url, tries=4):
    for k in range(tries):
        p = subprocess.run(["curl", "-sS", "--max-time", "30", url],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip().startswith("{"):
            try:
                d = json.loads(p.stdout)
                if d.get("code") == "0":
                    return d["data"]
            except json.JSONDecodeError:
                pass
        time.sleep(1.5 * (k + 1))
    return None


def universe(top):
    """Perpetuos USDT ordenados por volume em DOLAR de 24h.

    volCcy24h vem em moeda base, entao ordenar por ele coloca memecoins de preco
    unitario minusculo no topo. Multiplicar pelo ultimo preco corrige isso.
    """
    data = get(TICKERS)
    if not data:
        raise SystemExit("nao consegui a lista de instrumentos")
    rows = [x for x in data if x["instId"].endswith("-USDT-SWAP")]
    for x in rows:
        x["usd"] = float(x["volCcy24h"]) * float(x["last"])
    rows.sort(key=lambda x: -x["usd"])
    return [x["instId"] for x in rows[:top]]


def fetch_symbol(inst, pages, sleep):
    rows, after = [], None
    for _ in range(pages):
        u = f"{CANDLES}?instId={inst}&bar=1Dutc&limit=100"
        if after:
            u += f"&after={after}"
        d = get(u)
        if not d:
            break
        rows.extend(d)
        after = d[-1][0]
        time.sleep(sleep)
        if len(d) < 100:
            break
    return rows


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.environ.get("DELTA_XS_DATA", os.path.join(here, "data")))
    ap.add_argument("--top", type=int, default=140)
    ap.add_argument("--pages", type=int, default=20, help="100 barras por pagina")
    ap.add_argument("--sleep", type=float, default=0.12, help="~8 req/s, sob o limite da OKX")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    insts = universe(a.top)
    json.dump(insts, open(os.path.join(a.out, "_universe.json"), "w"))
    done = 0
    for inst in insts:
        out = os.path.join(a.out, inst + ".json")
        if os.path.exists(out):
            done += 1
            continue
        raw = fetch_symbol(inst, a.pages, a.sleep)
        if not raw:
            print("FALHOU", inst, flush=True)
            continue
        recs = []
        for r in raw:
            # ts, o, h, l, c, vol(contratos), volCcy(base), volCcyQuote(USDT), confirm
            if len(r) >= 9 and r[8] != "1":
                continue          # barra nao confirmada: descarta
            recs.append({
                "date": dt.datetime.utcfromtimestamp(int(r[0]) / 1000).date().isoformat(),
                "open": float(r[1]), "high": float(r[2]), "low": float(r[3]),
                "close": float(r[4]),
                "volume_usd": float(r[7]) if len(r) > 7 and r[7] else None,
            })
        recs.sort(key=lambda x: x["date"])
        json.dump(recs, open(out, "w"))
        done += 1
        print(f"{done}/{len(insts)} {inst} {len(recs)} barras "
              f"{recs[0]['date']}..{recs[-1]['date']}", flush=True)
    print("CONCLUIDO", done, "simbolos em", a.out, flush=True)


if __name__ == "__main__":
    main()
