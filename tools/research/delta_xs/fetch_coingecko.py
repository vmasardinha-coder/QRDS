"""Coletor CoinGecko: painel diario que RETEM ativos mortos.

PESQUISA APENAS. Endpoints publicos de mercado, sem ordem, sem endpoint privado.
Nao le nem escreve ledger, nao toca parametro congelado.

POR QUE ESTA FONTE: a API da OKX purga instrumentos deslistados — FTT-USDT-SWAP
e SRM-USDT-SWAP retornam 51001. A CoinGecko mantem os mortos: verificado em
2026-10-14 que ftx-token e terra-luna devolvem historico diario completo. Para
medir o escore sem vies de sobrevivencia e preciso de uma fonte assim.

LIMITE DURO DESTA CHAVE: chaves do plano demo so servem 365 dias de historico
(error_code 10012 fora disso). Um painel de 365 dias NAO satisfaz o portao
historico do contrato V14, que exige min_days=1000 e t>=3.0 — pela potencia, o
t maximo esperado em 365 dias e da ordem de 1.4. Este painel serve para MEDIR O
VIES comparando com a OKX na mesma janela, nao para avaliar o portao.

Uso:
    python3 -I fetch_coingecko.py --top 400
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time

BASE = "https://api.coingecko.com/api/v3"


def keys() -> list[str]:
    raw = os.environ.get("COINGECKO_API_KEYS", "")
    ks = [x.strip() for x in raw.replace(";", ",").split(",") if x.strip()]
    if not ks:
        raise SystemExit("COINGECKO_API_KEYS nao definida no ambiente")
    return ks


def get(url, key, tries=4):
    for k in range(tries):
        p = subprocess.run(
            ["curl", "-sS", "--max-time", "45", "-H", f"x-cg-demo-api-key: {key}", url],
            capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip()[:1] in "[{":
            try:
                d = json.loads(p.stdout)
            except json.JSONDecodeError:
                d = None
            if d is not None and not (isinstance(d, dict) and "error" in d):
                return d
        time.sleep(3.0 * (k + 1))   # 429 e comum no plano demo
    return None


def universe(top, key, sleep):
    """Top N por market cap ATUAL. Superset de onde o ranking ponto-no-tempo sai.

    Ainda e um superset escolhido hoje: moedas que cairam abaixo do rank `top`
    ficam de fora. Mas como a CoinGecko retem os mortos, uma moeda que colapsou
    continua listada com valor residual, entao a fuga e muito menor que na OKX.
    Quanto maior o `top`, menor o residuo.
    """
    out = []
    for page in range(1, top // 250 + 2):
        per = min(250, top - len(out))
        if per <= 0:
            break
        d = get(f"{BASE}/coins/markets?vs_currency=usd&order=market_cap_desc"
                f"&per_page={per}&page={page}", key)
        if not d:
            break
        out.extend([c["id"] for c in d])
        time.sleep(sleep)
    return out[:top]


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.environ.get("DELTA_XS_CG_DATA",
                                                    os.path.join(here, "data_cg")))
    ap.add_argument("--top", type=int, default=400)
    ap.add_argument("--sleep", type=float, default=2.2, help="plano demo ~30 req/min")
    a = ap.parse_args()

    ks = keys()
    os.makedirs(a.out, exist_ok=True)
    upath = os.path.join(a.out, "_universe.json")
    if os.path.exists(upath):
        ids = json.load(open(upath))
    else:
        ids = universe(a.top, ks[0], a.sleep)
        json.dump(ids, open(upath, "w"))
    print(f"universo: {len(ids)} moedas", flush=True)

    done = 0
    for n, cid in enumerate(ids):
        out = os.path.join(a.out, cid + ".json")
        if os.path.exists(out):
            done += 1
            continue
        key = ks[n % len(ks)]          # alterna as chaves disponiveis
        d = get(f"{BASE}/coins/{cid}/market_chart?vs_currency=usd&days=365&interval=daily", key)
        time.sleep(a.sleep)
        if not d or not d.get("prices"):
            print("FALHOU", cid, flush=True)
            continue
        caps = {int(t): v for t, v in d.get("market_caps", [])}
        vols = {int(t): v for t, v in d.get("total_volumes", [])}
        recs = []
        for t, px in d["prices"]:
            t = int(t)
            recs.append({
                "date": dt.datetime.utcfromtimestamp(t / 1000).date().isoformat(),
                "close": px,
                "market_cap": caps.get(t),
                "volume_usd": vols.get(t),
            })
        recs.sort(key=lambda x: x["date"])
        json.dump(recs, open(out, "w"))
        done += 1
        if done % 25 == 0 or done < 3:
            print(f"{done}/{len(ids)} {cid} {len(recs)} barras "
                  f"{recs[0]['date']}..{recs[-1]['date']}", flush=True)
    print("CONCLUIDO", done, "moedas em", a.out, flush=True)


if __name__ == "__main__":
    main()
