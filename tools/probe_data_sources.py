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


def probe_nasdaq_deep() -> str:
    """Os dois pontos que decidem se a Nasdaq serve como fonte primaria:
    (1) chega a 260+ pregoes? (2) o SPY, que e ETF, tem classe propria?
    (3) aguenta pedidos seguidos sem limitar por taxa?
    """
    out = []
    end = datetime.now(timezone.utc).date()

    def fetch(ticker, assetclass, days):
        start = end - timedelta(days=days)
        url = (f"https://api.nasdaq.com/api/quote/{ticker}/historical"
               f"?assetclass={assetclass}&fromdate={start}&todate={end}&limit=9999")
        status, body = _get(url)
        data = json.loads(body.decode("utf-8"))
        rows = (((data.get("data") or {}).get("tradesTable") or {}).get("rows")) or []
        return status, rows

    for days in (400, 800, 1200):
        try:
            status, rows = fetch("AAPL", "stocks", days)
            flag = "OK" if len(rows) >= 260 else "curto"
            span = f"{rows[-1]['date']} -> {rows[0]['date']}" if rows else "-"
            out.append(f"    {flag:5s} AAPL {days}d: {len(rows):>4} pregoes  {span}")
        except Exception as err:  # noqa: BLE001
            out.append(f"    FALHOU AAPL {days}d: {type(err).__name__}")

    for assetclass in ("etf", "stocks", "index"):
        try:
            status, rows = fetch("SPY", assetclass, 800)
            out.append(f"    SPY assetclass={assetclass}: HTTP {status}, "
                       f"{len(rows)} pregoes")
        except Exception as err:  # noqa: BLE001
            out.append(f"    SPY assetclass={assetclass}: FALHOU {type(err).__name__}")

    # rajada: 12 pedidos seguidos, como no ciclo real
    ok = 0
    erro = ""
    for tk in ["MSFT", "NVDA", "JPM", "V", "UNH", "XOM", "LLY", "JNJ",
               "PG", "MA", "HD", "COST"]:
        try:
            _, rows = fetch(tk, "stocks", 800)
            if rows:
                ok += 1
        except Exception as err:  # noqa: BLE001
            erro = f"{tk}: {type(err).__name__} {str(err)[:60]}"
            break
    out.append(f"    rajada de 12 pedidos seguidos: {ok} ok"
               + (f" · parou em {erro}" if erro else " · sem limite de taxa"))
    return "\n" + "\n".join(out)


def probe_stockanalysis(ticker: str = "AAPL") -> str:
    """Precisa de >= 260 pregoes para o momentum 12-1; ve qual variante os da."""
    variants = [
        f"https://stockanalysis.com/api/symbol/s/{ticker}/history",
        f"https://stockanalysis.com/api/symbol/s/{ticker}/history?range=2Y",
        f"https://stockanalysis.com/api/symbol/s/{ticker}/history?range=5Y",
        f"https://stockanalysis.com/api/symbol/s/{ticker}/history?period=Daily&range=2Y",
    ]
    out = []
    for url in variants:
        try:
            status, body = _get(url)
            rows = (json.loads(body.decode("utf-8")).get("data") or {}).get("data") or []
            span = f"{rows[-1]['t']} -> {rows[0]['t']}" if rows else "-"
            flag = "OK" if len(rows) >= 260 else "curto"
            out.append(f"    {flag:5s} {len(rows):>4} pregoes  {span}  "
                       f"[{url.split('history')[1] or '(sem parametros)'}]")
        except Exception as err:  # noqa: BLE001
            out.append(f"    FALHOU {type(err).__name__} [{url[-40:]}]")
    campos = ""
    try:
        _, body = _get(variants[0])
        rows = (json.loads(body.decode("utf-8")).get("data") or {}).get("data") or []
        if rows:
            campos = f"\n    campos: {sorted(rows[0].keys())}"
    except Exception:  # noqa: BLE001
        pass
    return "\n" + "\n".join(out) + campos


def probe_stockanalysis_b3(ticker: str = "PETR4") -> str:
    """A B3 na stockanalysis usa o prefixo de bolsa."""
    out = []
    for path in (f"quote/bsp/{ticker}/history", f"symbol/s/{ticker}/history"):
        url = f"https://stockanalysis.com/api/{path}"
        try:
            status, body = _get(url)
            rows = (json.loads(body.decode("utf-8")).get("data") or {}).get("data") or []
            out.append(f"    HTTP {status} · {len(rows)} pregoes [{path}]")
        except Exception as err:  # noqa: BLE001
            out.append(f"    FALHOU {type(err).__name__} [{path}]")
    return "\n" + "\n".join(out)


def probe_yahoo(ticker: str = "SPY") -> str:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?range=1mo&interval=1d")
    status, body = _get(url)
    return f"HTTP {status} · {len(body)} bytes (controlo)"


def probe_stooq(ticker: str = "spy.us") -> str:
    status, body = _get(f"https://stooq.com/q/d/l/?s={ticker}&i=d")
    head = body[:90].decode("utf-8", "replace").replace("\n", " ")
    return f"HTTP {status} · inicio {head!r} (controlo)"


def _brapi(ticker: str, rng: str = "2y"):
    """O token vai no cabecalho, nunca na query string — os logs do Actions
    sao publicos neste repositorio, tal como os relatorios.
    """
    import os
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    url = (f"https://brapi.dev/api/quote/{ticker}"
           f"?range={rng}&interval=1d&fundamental=false")
    status, body = _get(url, headers=headers)
    return status, json.loads(body.decode("utf-8"))


def probe_brapi(ticker: str = "PETR4") -> str:
    import os
    status, data = _brapi(ticker)
    hist = ((data.get("results") or [{}])[0].get("historicalDataPrice")) or []
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    return (f"HTTP {status} · token {'presente' if token else 'AUSENTE'} · "
            f"{len(hist)} pregoes")


# Candidatos a substituir tickers que sairam da B3 por evento societario,
# com os antigos e dois controlos vivos na mesma corrida. O nome da empresa
# e o que confirma a identidade: um simbolo que responde nao prova ser o
# sucessor certo.
B3_CANDIDATOS = ["CPLE3", "CPLE5", "CPLE6", "MBRF3", "BRFS3", "PETR4", "VALE3"]


def probe_b3_tickers(tickers: list[str] | None = None) -> str:
    out = []
    for tk in tickers or B3_CANDIDATOS:
        try:
            status, data = _brapi(tk)
        except urllib.error.HTTPError as err:
            # O corpo do erro e que distingue "simbolo nao existe" de "o teu
            # plano nao da acesso a este simbolo" — sem ele, um 400 nao diz
            # se a correcao e trocar o ticker ou mudar de fonte.
            corpo = ""
            try:
                corpo = err.read().decode("utf-8", "replace")[:200]
            except Exception:  # noqa: BLE001
                pass
            out.append(f"    {tk:8s} HTTP {err.code} {err.reason} · corpo={corpo!r}")
            continue
        except Exception as err:  # noqa: BLE001
            out.append(f"    {tk:8s} FALHOU {type(err).__name__}")
            continue
        res = (data.get("results") or [{}])[0]
        hist = res.get("historicalDataPrice") or []
        ultimo = "-"
        if hist:
            ts = hist[-1].get("date")
            if isinstance(ts, (int, float)):
                ultimo = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        flag = "OK" if len(hist) >= 260 else ("curto" if hist else "VAZIO")
        out.append(f"    {flag:5s} {tk:8s} HTTP {status} · {len(hist):>4} pregoes"
                   f" · ate {ultimo} · nome={res.get('longName') or res.get('shortName')!r}"
                   f" · preco={res.get('regularMarketPrice')}")
    return "\n" + "\n".join(out)


def probe_brapi_disponiveis(buscas: list[str] | None = None) -> str:
    """Pergunta a fonte que simbolos ela tem, em vez de adivinhar candidatos.

    Adivinhar o sucessor de um ticker extinto e como escolher fonte as cegas:
    testa-se uma hipotese de cada vez e nunca se sabe o espaco todo.
    """
    import os
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    out = []
    for termo in buscas or ["CPLE", "COPEL", "MBRF", "BRF", "MRFG"]:
        url = f"https://brapi.dev/api/available?search={termo}"
        try:
            _, body = _get(url, headers=headers)
            achados = (json.loads(body.decode("utf-8")).get("stocks")) or []
        except urllib.error.HTTPError as err:
            out.append(f"    {termo:8s} HTTP {err.code} {err.reason}")
            continue
        except Exception as err:  # noqa: BLE001
            out.append(f"    {termo:8s} FALHOU {type(err).__name__}")
            continue
        out.append(f"    {termo:8s} {len(achados):>3} simbolos: {achados[:25]}")
    return "\n" + "\n".join(out)


def probe_brapi_ranges(tickers: list[str] | None = None) -> str:
    """Quanto historico a fonte da, por ticker e por range.

    CPLE3 e MBRF3 existem na brapi mas recusam range=2y com INVALID_RANGE,
    enquanto PETR4 aceita — logo a restricao e por ticker, nao do plano
    inteiro. O momentum 12-1 precisa de ~260 pregoes: se o maior range
    aceite nao chegar la, trocar o ticker nao resolve nada.
    """
    out = []
    for tk in tickers or ["CPLE3", "MBRF3", "PETR4"]:
        linha = [f"    {tk:8s}"]
        for rng in ("2y", "1y", "6mo", "3mo", "1mo"):
            try:
                _, data = _brapi(tk, rng)
                hist = ((data.get("results") or [{}])[0]
                        .get("historicalDataPrice")) or []
                linha.append(f"{rng}={len(hist)}")
            except urllib.error.HTTPError as err:
                linha.append(f"{rng}=HTTP{err.code}")
            except Exception as err:  # noqa: BLE001
                linha.append(f"{rng}={type(err).__name__}")
        out.append(" ".join(linha))
    return "\n" + "\n".join(out)


def probe_cotahist() -> str:
    """Serie historica oficial da B3 (COTAHIST): um ficheiro anual com todos
    os pregoes de todos os papeis.

    Interessa porque devolve serie diaria, e nao um retrato pre-calculado:
    com ela a estrategia fica identica e a troca e so de fonte. O ficheiro do
    ano passado nunca muda, por isso pode ser guardado em cache como o CDI.

    So le os primeiros bytes — nao vale a pena trazer 25 MB para saber se a
    porta esta aberta.
    """
    ano = datetime.now(timezone.utc).year
    bases = [
        "https://bvmf.bmfbovespa.com.br/InstDados/SerHist",
        "https://www.b3.com.br/InstDados/SerHist",
    ]
    out = []
    for base in bases:
        for nome in (f"COTAHIST_A{ano}.ZIP", f"COTAHIST_A{ano - 1}.ZIP"):
            url = f"{base}/{nome}"
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": UA, "Range": "bytes=0-1023"})
                with urllib.request.urlopen(req, timeout=30) as resp:
                    trecho = resp.read(1024)
                    tamanho = resp.headers.get("Content-Range") or \
                        resp.headers.get("Content-Length")
                    zip_ok = trecho[:2] == b"PK"
                    out.append(f"    HTTP {resp.status} · {nome} · "
                               f"tamanho={tamanho} · zip={zip_ok} "
                               f"[{base.split('/')[2]}]")
            except urllib.error.HTTPError as err:
                out.append(f"    HTTP {err.code} {err.reason} · {nome} "
                           f"[{base.split('/')[2]}]")
            except Exception as err:  # noqa: BLE001
                out.append(f"    FALHOU {type(err).__name__} · {nome} "
                           f"[{base.split('/')[2]}]")
    return "\n" + "\n".join(out)


def probe_tradingview_b3() -> str:
    """O plano B: retrato do scanner para a B3.

    Da os campos que a estrategia precisa ja calculados, mas nao da serie —
    adota-lo mudaria como o sinal e calculado, o que cai na seccao 6 da Carta.
    """
    return probe_tradingview("brazil", ["PETR4", "VALE3", "CPLE3", "MBRF3",
                                        "BOVA11", "ITUB4"])


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    print(f"Sonda de fontes — {datetime.now(timezone.utc).isoformat()}")

    if argv and argv[0] == "b3arquivo":
        # Ler o arquivo a serio, com o universo a serio. Os testes usam
        # registos montados a mao: provam o formato que eu assumi, nao o que
        # a B3 emite. So isto separa as duas coisas.
        from trading_agent import config, cotahist

        def ler() -> str:
            alvo = config.B3_UNIVERSE + [config.B3S_UNDERLYING]
            inicio = datetime.now(timezone.utc)
            series = cotahist.load(alvo)
            segundos = (datetime.now(timezone.utc) - inicio).total_seconds()
            curtos = sorted(t for t in alvo
                            if len(series.get(t, [])) < config.EQUITY_MIN_HISTORY_DAYS)
            ausentes = sorted(t for t in alvo if t not in series)
            exemplo = series.get("PETR4") or []
            return (
                f"{len(series)} de {len(alvo)} tickers em {segundos:.1f}s\n"
                f"    pregoes: min={min((len(v) for v in series.values()), default=0)}"
                f" max={max((len(v) for v in series.values()), default=0)}\n"
                f"    PETR4 ultimo: {exemplo[-1] if exemplo else '-'}\n"
                f"    PETR4 primeiro: {exemplo[0] if exemplo else '-'}\n"
                f"    ausentes ({len(ausentes)}): {ausentes}\n"
                f"    abaixo de {config.EQUITY_MIN_HISTORY_DAYS} pregoes "
                f"({len(curtos)}): {curtos}")

        report("COTAHIST — leitura real do universo da B3", ler)
        print("\nFim da sonda.")
        return 0

    if argv and argv[0] == "b3fonte":
        # Procurar substituto para a brapi na B3. A ordem reflecte a
        # preferencia: primeiro a que preserva a estrategia.
        report("B3 COTAHIST — serie oficial (preserva a estrategia)",
               probe_cotahist)
        report("TradingView scanner — B3 (retrato, muda a metodologia)",
               probe_tradingview_b3)
        print("\nFim da sonda.")
        return 0

    if argv and argv[0] == "b3tickers":
        # Modo dirigido: so os simbolos da B3, sem gastar pedidos nas outras
        # fontes. Usado quando um evento societario muda um ticker.
        report("brapi.dev — que simbolos a fonte tem", probe_brapi_disponiveis)
        report("brapi.dev — historico por ticker e range", probe_brapi_ranges)
        report("brapi.dev — identidade de tickers B3", probe_b3_tickers)
        print("\nFim da sonda.")
        return 0

    report("TradingView scanner — EUA (lote de 5)",
           lambda: probe_tradingview("america",
                                     ["AAPL", "MSFT", "NVDA", "JPM", "SPY"]))
    report("Nasdaq API — profundidade, SPY e rajada", probe_nasdaq_deep)
    report("brapi.dev — historico B3", probe_brapi)
    report("brapi.dev — que simbolos a fonte tem", probe_brapi_disponiveis)
    report("brapi.dev — historico por ticker e range", probe_brapi_ranges)
    report("brapi.dev — identidade de tickers B3", probe_b3_tickers)
    report("Yahoo (controlo — esperado bloqueio)", probe_yahoo)
    report("Stooq (controlo — esperado bloqueio)", probe_stooq)
    print("\nFim da sonda.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
