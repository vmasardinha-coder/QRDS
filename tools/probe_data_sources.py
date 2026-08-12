"""Sonda candidatas a fonte de dados, de dentro do runner do GitHub Actions.

Existe porque o ambiente de desenvolvimento nao alcanca estes hosts: sem
correr aqui, escolher fonte seria adivinhar. Nao altera nada do agente —
so imprime o que cada candidata responde, para a decisao ser tomada com
evidencia.

Uso: python -m tools.probe_data_sources
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

TV_COLUMNS = ["name", "close", "SMA200", "Perf.Y", "Perf.1M",
              "Volatility.D", "average_volume_60d_calc"]


def _get(url: str, data: bytes | None = None,
         headers: dict | None = None, timeout: float = 25.0):
    head = {"User-Agent": UA}
    if data is not None:
        head["Content-Type"] = "application/json"
    head.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=head)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read()


def report(name: str, fn) -> None:
    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
    try:
        verdict = fn()
    except urllib.error.HTTPError as err:
        print(f"  FALHOU  HTTP {err.code} {err.reason}")
        return
    except Exception as err:  # noqa: BLE001 - a sonda tem de sobreviver a tudo
        print(f"  FALHOU  {type(err).__name__}: {str(err)[:160]}")
        return
    print(f"  {verdict}")


def probe_tradingview(market: str, names: list[str]) -> str:
    payload = json.dumps({
        "filter": [{"left": "name", "operation": "in_range", "right": names}],
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": TV_COLUMNS,
        "range": [0, 60],
    }).encode()
    status, body = _get(f"https://scanner.tradingview.com/{market}/scan",
                        data=payload)
    data = json.loads(body.decode("utf-8"))
    rows = data.get("data") or []
    if not rows:
        return f"HTTP {status} mas 0 linhas — resposta: {body[:160]!r}"
    sample = rows[0]
    pairs = dict(zip(TV_COLUMNS, sample.get("d", [])))
    return (f"HTTP {status} · {len(rows)} de {len(names)} simbolos\n"
            f"  exemplo {sample.get('s')}: {pairs}")


def probe_nasdaq(ticker: str = "AAPL") -> str:
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=400)
    url = (f"https://api.nasdaq.com/api/quote/{ticker}/historical"
           f"?assetclass=stocks&fromdate={start}&todate={end}&limit=9999")
    status, body = _get(url)
    data = json.loads(body.decode("utf-8"))
    rows = (((data.get("data") or {}).get("tradesTable") or {}).get("rows")) or []
    return f"HTTP {status} · {len(rows)} pregoes · exemplo {rows[0] if rows else '-'}"


def probe_stockanalysis(ticker: str = "AAPL") -> str:
    url = f"https://stockanalysis.com/api/symbol/s/{ticker}/history"
    status, body = _get(url)
    return f"HTTP {status} · {len(body)} bytes · inicio {body[:140]!r}"


def probe_yahoo(ticker: str = "SPY") -> str:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?range=1mo&interval=1d")
    status, body = _get(url)
    return f"HTTP {status} · {len(body)} bytes (controlo)"


def probe_stooq(ticker: str = "spy.us") -> str:
    status, body = _get(f"https://stooq.com/q/d/l/?s={ticker}&i=d")
    head = body[:90].decode("utf-8", "replace").replace("\n", " ")
    return f"HTTP {status} · inicio {head!r} (controlo)"


def probe_brapi(ticker: str = "PETR4") -> str:
    import os
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    url = (f"https://brapi.dev/api/quote/{ticker}"
           f"?range=2y&interval=1d&fundamental=false")
    if token:
        url += f"&token={token}"
    status, body = _get(url)
    data = json.loads(body.decode("utf-8"))
    hist = ((data.get("results") or [{}])[0].get("historicalDataPrice")) or []
    return (f"HTTP {status} · token {'presente' if token else 'AUSENTE'} · "
            f"{len(hist)} pregoes")


def main() -> int:
    print(f"Sonda de fontes — {datetime.now(timezone.utc).isoformat()}")
    report("TradingView scanner — EUA (lote de 5)",
           lambda: probe_tradingview("america",
                                     ["AAPL", "MSFT", "NVDA", "JPM", "SPY"]))
    report("TradingView scanner — Brasil (lote de 5)",
           lambda: probe_tradingview("brazil",
                                     ["PETR4", "VALE3", "ITUB4", "BOVA11", "WEGE3"]))
    report("Nasdaq API — historico diario", probe_nasdaq)
    report("stockanalysis.com — historico", probe_stockanalysis)
    report("brapi.dev — historico B3", probe_brapi)
    report("Yahoo (controlo — esperado bloqueio)", probe_yahoo)
    report("Stooq (controlo — esperado bloqueio)", probe_stooq)
    print("\nFim da sonda.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
