"""Coletor data.binance.vision: historico longo QUE RETEM DESLISTADOS.

PESQUISA APENAS. Arquivo publico, sem chave, sem credencial, sem ordem, sem
endpoint privado. Nao le nem escreve ledger, nao toca parametro congelado.

POR QUE ESTA FONTE RESOLVE O PROBLEMA:

  OKX        purga deslistados          -> so sobreviventes
  CoinGecko  retem mortos, mas as chaves demo dao so 365 dias
  Binance Vision  retem TUDO, de graca, 5+ anos

Verificado em 2026-10-14: FTTUSDT, SRMUSDT, LUNAUSDT, ANCUSDT, RAYUSDT e
BTSUSDT — todos deslistados — continuam no arquivo com historico completo.
Sao 900 perpetuos USDT ja listados algum dia, contra os 140 vivos que a OKX
mostra. Um nome deslistado simplesmente para de ter barras na data em que
saiu, que e exatamente o comportamento correto: sem look-ahead, sem
preenchimento, e sem o sobrevivente fantasma.

Uso:
    python3 -I fetch_binance_vision.py --since 2021-04
    python3 -I fetch_binance_vision.py --jobs 24
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import subprocess
import urllib.parse
import zipfile
from concurrent.futures import ThreadPoolExecutor

S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
DL = "https://data.binance.vision"
PREFIX = "data/futures/um/monthly/klines/"


def curl(url, binary=False, tries=3):
    for k in range(tries):
        p = subprocess.run(["curl", "-sS", "--max-time", "60", url],
                           capture_output=True)
        if p.returncode == 0 and p.stdout:
            return p.stdout if binary else p.stdout.decode("utf-8", "replace")
    return None


def all_usdt_perps() -> list[str]:
    """Todo perpetuo USDT ja listado, vivo ou morto."""
    syms, marker = [], None
    while True:
        u = f"{S3}?delimiter=/&prefix={urllib.parse.quote(PREFIX)}"
        if marker:
            u += "&marker=" + urllib.parse.quote(marker)
        s = curl(u)
        if not s:
            break
        got = re.findall(r"<Prefix>" + re.escape(PREFIX) + r"([^/]+)/</Prefix>", s)
        if not got:
            break
        syms += got
        if "<IsTruncated>true" not in s:
            break
        marker = PREFIX + got[-1] + "/"
    return [x for x in syms if x.endswith("USDT")]


def months_for(sym: str) -> list[str]:
    """Meses que existem no arquivo para este simbolo (evita tentar 404)."""
    pref = f"{PREFIX}{sym}/1d/"
    s = curl(f"{S3}?prefix={urllib.parse.quote(pref)}")
    if not s:
        return []
    return sorted(set(re.findall(re.escape(sym) + r"-1d-(\d{4}-\d{2})\.zip", s)))


def fetch_symbol(sym, since, out_dir):
    out = os.path.join(out_dir, sym + ".json")
    if os.path.exists(out):
        return sym, -1
    months = [m for m in months_for(sym) if m >= since]
    if not months:
        return sym, 0
    recs = {}
    for m in months:
        blob = curl(f"{DL}/{PREFIX}{sym}/1d/{sym}-1d-{m}.zip", binary=True)
        if not blob:
            continue
        try:
            z = zipfile.ZipFile(io.BytesIO(blob))
        except zipfile.BadZipFile:
            continue
        for name in z.namelist():
            for row in csv.reader(io.TextIOWrapper(z.open(name), "utf-8")):
                if not row or not row[0].strip().isdigit():
                    continue      # alguns arquivos trazem cabecalho
                ts = int(row[0])
                if ts > 10 ** 12 * 10:
                    ts //= 1000   # alguns meses vem em microssegundos
                try:
                    close = float(row[4])
                    quote_vol = float(row[7])
                except (ValueError, IndexError):
                    continue
                if close <= 0:
                    continue
                recs[ts] = {
                    "date": dt.datetime.utcfromtimestamp(ts / 1000).date().isoformat(),
                    "open": float(row[1]), "high": float(row[2]), "low": float(row[3]),
                    "close": close, "volume_usd": quote_vol,
                }
    if not recs:
        return sym, 0
    rows = sorted(recs.values(), key=lambda x: x["date"])
    json.dump(rows, open(out, "w"))
    return sym, len(rows)


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--out", default=os.environ.get("DELTA_XS_BV_DATA",
                                                    os.path.join(here, "data_bv")))
    ap.add_argument("--since", default="2021-04", help="primeiro mes, AAAA-MM")
    ap.add_argument("--jobs", type=int, default=16)
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    upath = os.path.join(a.out, "_universe.json")
    if os.path.exists(upath):
        syms = json.load(open(upath))
    else:
        syms = all_usdt_perps()
        json.dump(syms, open(upath, "w"))
    print(f"perpetuos USDT ja listados (vivos + mortos): {len(syms)}", flush=True)

    done = skipped = 0
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for sym, n in ex.map(lambda s: fetch_symbol(s, a.since, a.out), syms):
            if n == 0:
                skipped += 1
            else:
                done += 1
                if done % 50 == 0:
                    print(f"  {done} simbolos gravados", flush=True)
    print(f"CONCLUIDO: {done} com dados, {skipped} sem barras desde {a.since}",
          flush=True)


if __name__ == "__main__":
    main()
