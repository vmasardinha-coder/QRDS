"""Fontes publicas de dados de mercado (sem chave de API).

Cascatas por mercado, para nenhum bloqueio de uma fonte derrubar uma carteira:
  acoes EUA : Stooq -> Yahoo (query1, query2)
  acoes B3  : brapi.dev -> Yahoo
  crypto    : Coinbase -> Binance -> CoinGecko
  CDI       : SGS do Banco Central (4 formas de consulta) -> copia local

Todas as funcoes de preco devolvem series diarias ordenadas por data ascendente:
lista de tuplos (date_iso: str, close: float, volume: float). O volume alimenta
o filtro de liquidez da Carta de Operacao (secao 5); quando a fonte nao o
fornece, vem 0.0 e o ativo e tratado como nao elegivel (fail-closed, secao 7).
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
RETRIES = 3
RETRY_SLEEP_S = 3.0
RATE_LIMIT_SLEEP_S = (20.0, 45.0, 90.0)   # esperas para HTTP 429
MAX_RETRY_AFTER_S = 120.0


class DataSourceError(RuntimeError):
    pass


class SourceUnavailable(DataSourceError):
    """A fonte esta em baixo ou a bloquear-nos — distinto de o ativo nao existir."""


class RateLimited(SourceUnavailable):
    """A fonte respondeu 429: esta a recusar por volume, nao por ativo."""


# 4xx que significam "nao existe / nao autorizado": repetir nao muda o
# resultado e, com universos grandes, custa dezenas de minutos por ciclo.
PERMANENT_HTTP = {400, 401, 403, 404, 410, 422}


def _http_get(url: str, timeout: float = 30.0,
              retries: int | None = None) -> bytes:
    last_err: Exception | None = None
    for attempt in range(retries or RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in PERMANENT_HTTP:
                raise DataSourceError(f"GET {url}: HTTP {err.code} (definitivo)")
            if err.code == 429:
                # a fonte pede para abrandar; obedece ao cabecalho se houver
                wait = RATE_LIMIT_SLEEP_S[min(attempt, len(RATE_LIMIT_SLEEP_S) - 1)]
                header = (err.headers or {}).get("Retry-After")
                if header:
                    try:
                        wait = max(wait, min(float(header), MAX_RETRY_AFTER_S))
                    except (TypeError, ValueError):
                        pass
                time.sleep(wait)
                continue
            time.sleep(RETRY_SLEEP_S * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            last_err = err
            time.sleep(RETRY_SLEEP_S * (attempt + 1))
    attempts = retries or RETRIES
    if isinstance(last_err, urllib.error.HTTPError) and last_err.code == 429:
        raise RateLimited(f"GET {url}: 429 apos {attempts} tentativas")
    raise DataSourceError(f"GET {url} falhou apos {attempts} tentativas: {last_err}")


def fetch_stooq_daily(ticker: str) -> list[tuple[str, float, float]]:
    """Serie diaria de fecho para um ticker dos EUA via Stooq."""
    symbol = ticker.lower().replace(".", "-") + ".us"
    try:
        raw = _http_get(f"https://stooq.com/q/d/l/?s={symbol}&i=d")
    except DataSourceError as err:
        raise SourceUnavailable(str(err))
    text = raw.decode("utf-8", errors="replace")
    # a Stooq responde 200 com uma pagina de excesso de pedidos: e a fonte a
    # bloquear, nao o ticker a nao existir
    if "exceeded" in text.lower() or "limit" in text[:200].lower():
        raise SourceUnavailable(f"Stooq bloqueou o pedido ({ticker})")
    rows: list[tuple[str, float, float]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        try:
            close = float(row["Close"])
            date = row["Date"]
            volume = float(row.get("Volume") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if close > 0:
            rows.append((date, close, volume))
    if len(rows) < 10:
        # CSV valido mas sem dados: este ticker nao existe na Stooq. Nao e
        # motivo para desistir da fonte inteira.
        raise DataSourceError(f"Stooq nao tem serie para {ticker}")
    rows.sort(key=lambda r: r[0])
    return rows


BENCHMARK_RETRIES = 6
# query1 e query2 sao edges distintos do mesmo servico; quando um limita por
# taxa, o outro por vezes ainda responde.
YAHOO_HOSTS = ("https://query1.finance.yahoo.com",
               "https://query2.finance.yahoo.com")

_YAHOO_RATE_LIMITED = False
_YAHOO_TRIP_AFTER = 2          # respostas 429 antes de desistir do ciclo
_yahoo_rate_limit_hits = 0


def reset_source_breakers() -> None:
    """Repoe os disjuntores. Cada ciclo corre num processo novo, mas os testes
    e uma eventual reexecucao no mesmo processo precisam disto explicito."""
    global _YAHOO_RATE_LIMITED, _yahoo_rate_limit_hits
    global _STOOQ_CONSECUTIVE_FAILURES
    _YAHOO_RATE_LIMITED = False
    _yahoo_rate_limit_hits = 0
    _STOOQ_CONSECUTIVE_FAILURES = 0
    SOURCE_TALLY.clear()


def fetch_yahoo_daily(ticker: str,
                      retries: int | None = None) -> list[tuple[str, float, float]]:
    """Serie diaria de fecho via API de chart do Yahoo Finance (sem chave)."""
    symbol = ticker.upper()
    # tickers dos EUA usam '-' em vez de '.' (BRK.B); indices (^BVSP) e
    # tickers da B3 (.SA) ficam como estao
    if not (symbol.startswith("^") or symbol.endswith(".SA")):
        symbol = symbol.replace(".", "-")
    symbol = urllib.parse.quote(symbol)
    global _YAHOO_RATE_LIMITED, _yahoo_rate_limit_hits
    if _YAHOO_RATE_LIMITED:
        raise RateLimited("Yahoo ja recusou por volume neste ciclo; "
                          "nao insisto ativo a ativo")
    last: Exception | None = None
    data = None
    for host in YAHOO_HOSTS:
        url = (f"{host}/v8/finance/chart/{symbol}"
               f"?range=2y&interval=1d&events=div%2Csplit")
        try:
            data = json.loads(_http_get(url, retries=retries).decode("utf-8"))
            _yahoo_rate_limit_hits = 0
            break
        except RateLimited as err:
            last = err
            _yahoo_rate_limit_hits += 1
            if _yahoo_rate_limit_hits >= _YAHOO_TRIP_AFTER:
                _YAHOO_RATE_LIMITED = True
                raise RateLimited(
                    f"Yahoo a limitar por volume ({_yahoo_rate_limit_hits} vezes); "
                    f"desisto da fonte neste ciclo")
        except DataSourceError as err:
            last = err
    if data is None:
        raise DataSourceError(str(last))
    try:
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        closes = quote["close"]
        volumes = quote.get("volume") or [None] * len(closes)
    except (KeyError, IndexError, TypeError) as err:
        raise DataSourceError(f"Yahoo: resposta inesperada para {ticker}: {err}")
    dedup: dict[str, tuple[float, float]] = {}
    for ts, close, volume in zip(timestamps, closes, volumes):
        if close is None:
            continue
        date = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
        # o mesmo dia pode aparecer duas vezes (sessao em curso); mantem o ultimo
        dedup[date] = (float(close), float(volume or 0.0))
    if len(dedup) < 10:
        raise DataSourceError(f"Yahoo devolveu serie vazia para {ticker}")
    return [(d, c, v) for d, (c, v) in sorted(dedup.items())]


_STOOQ_CONSECUTIVE_FAILURES = 0
_STOOQ_TRIP_AFTER = 3

# Contagem por fonte, para o relatorio dizer de onde vieram os dados em vez
# de eu ter de adivinhar quando algo corre mal.
SOURCE_TALLY: dict[str, int] = {}


def fetch_equity_daily(ticker: str,
                       is_benchmark: bool = False) -> list[tuple[str, float, float]]:
    """Stooq como fonte primaria, Yahoo Finance como fallback.

    Depois de _STOOQ_TRIP_AFTER falhas consecutivas do Stooq (tipico quando
    bloqueia IPs de cloud), os pedidos seguintes vao direto ao Yahoo.
    """
    from . import config
    global _STOOQ_CONSECUTIVE_FAILURES
    if _STOOQ_CONSECUTIVE_FAILURES < _STOOQ_TRIP_AFTER:
        try:
            series = fetch_stooq_daily(ticker)
            _STOOQ_CONSECUTIVE_FAILURES = 0
            SOURCE_TALLY["stooq"] = SOURCE_TALLY.get("stooq", 0) + 1
            time.sleep(config.FETCH_DELAY_S)
            return series
        except SourceUnavailable:
            _STOOQ_CONSECUTIVE_FAILURES += 1   # so falhas da fonte contam
        except DataSourceError:
            pass                               # ticker inexistente: segue para o Yahoo
    series = fetch_yahoo_daily(
        ticker, retries=BENCHMARK_RETRIES if is_benchmark else None)
    SOURCE_TALLY["yahoo"] = SOURCE_TALLY.get("yahoo", 0) + 1
    time.sleep(config.FETCH_DELAY_S)
    return series


def fetch_coinbase_daily(asset: str, days: int = 420) -> list[tuple[str, float, float]]:
    """Serie diaria de fecho (UTC) para <asset>-USD via Coinbase Exchange.

    A API limita a 300 velas por pedido; pagina em janelas de 250 dias.
    """
    product = f"{asset.upper()}-USD"
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    out: dict[str, tuple[float, float]] = {}
    window = 250
    cursor_end = end + timedelta(days=1)
    remaining = days
    while remaining > 0:
        span = min(window, remaining)
        cursor_start = cursor_end - timedelta(days=span)
        url = (
            f"https://api.exchange.coinbase.com/products/{product}/candles"
            f"?granularity=86400&start={cursor_start.strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f"&end={cursor_end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
        )
        data = json.loads(_http_get(url).decode("utf-8"))
        if not isinstance(data, list):
            raise DataSourceError(f"Coinbase: resposta inesperada para {product}: {data!r}")
        for candle in data:
            # [time, low, high, open, close, volume]
            ts, close, volume = int(candle[0]), float(candle[4]), float(candle[5])
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            out[date] = (close, volume)
        cursor_end = cursor_start
        remaining -= span
        time.sleep(0.34)  # limite de taxa publico da Coinbase
    if len(out) < 10:
        raise DataSourceError(f"Coinbase devolveu serie vazia para {product}")
    return [(d, c, v) for d, (c, v) in sorted(out.items())]


def fetch_coingecko_daily(coin_id: str, days: int = 365) -> list[tuple[str, float, float]]:
    """Fallback: serie diaria via CoinGecko (free tier)."""
    url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        f"?vs_currency=usd&days={days}"
    )
    data = json.loads(_http_get(url).decode("utf-8"))
    prices = data.get("prices")
    if not prices:
        raise DataSourceError(f"CoinGecko devolveu serie vazia para {coin_id}")
    volumes: dict[str, float] = {}
    for ms, vol in data.get("total_volumes") or []:
        date = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        volumes[date] = float(vol)
    out: dict[str, float] = {}
    for ms, price in prices:
        date = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        out[date] = float(price)
    # a CoinGecko devolve volume ja em USD; a Coinbase em unidades da moeda.
    # Normaliza para unidades da moeda para que close x volume seja giro em USD
    # em ambas as fontes, e o filtro de liquidez signifique a mesma coisa.
    return [(d, c, (volumes.get(d, 0.0) / c) if c > 0 else 0.0)
            for d, c in sorted(out.items())]


BINANCE_HOSTS = ("https://api.binance.com", "https://data-api.binance.vision")


def fetch_binance_daily(asset: str, days: int = 500) -> list[tuple[str, float, float]]:
    """Serie diaria via klines da Binance (par <ASSET>USDT, sem chave).

    Volume vem em unidades da moeda base, igual a Coinbase, por isso
    preco x volume continua a ser giro em USD para o filtro de liquidez.
    """
    symbol = f"{asset.upper()}USDT"
    last: Exception | None = None
    for host in BINANCE_HOSTS:
        url = (f"{host}/api/v3/klines?symbol={symbol}"
               f"&interval=1d&limit={min(days, 1000)}")
        try:
            data = json.loads(_http_get(url).decode("utf-8"))
        except DataSourceError as err:
            last = err
            continue
        if not isinstance(data, list) or len(data) < 10:
            last = DataSourceError(f"Binance sem serie para {symbol}")
            continue
        rows: list[tuple[str, float, float]] = []
        for k in data:
            # [openTime, open, high, low, close, volume, closeTime, ...]
            date = datetime.fromtimestamp(int(k[0]) / 1000,
                                          tz=timezone.utc).strftime("%Y-%m-%d")
            rows.append((date, float(k[4]), float(k[5])))
        rows.sort(key=lambda r: r[0])
        return rows
    raise DataSourceError(f"Binance indisponivel para {symbol}: {last}")


def fetch_crypto_daily(asset: str, coingecko_id: str) -> list[tuple[str, float, float]]:
    """Coinbase -> Binance -> CoinGecko.

    A Coinbase vem primeiro por cotar em USD verdadeiro; a Binance cobre os
    ativos que a Coinbase nao lista (foi o que falhou em 12 dos 150); a
    CoinGecko fica como ultima linha por dar volume global, que sobrestima a
    liquidez executavel numa unica bolsa.
    """
    for name, fetch in (("coinbase", lambda: fetch_coinbase_daily(asset)),
                        ("binance", lambda: fetch_binance_daily(asset)),
                        ("coingecko", lambda: fetch_coingecko_daily(coingecko_id))):
        try:
            series = fetch()
        except DataSourceError:
            continue
        SOURCE_TALLY[name] = SOURCE_TALLY.get(name, 0) + 1
        return series
    raise DataSourceError(f"Sem fonte para {asset} (Coinbase, Binance, CoinGecko)")

# O plano livre da brapi limita o intervalo devolvido; pede-se do mais longo
# para o mais curto e fica-se pelo primeiro que sirva. Menos de 260 pregoes
# nao chega para o momentum 12-1, mas chega para o benchmark e para o regime.
BRAPI_RANGES = ("2y", "1y", "6mo", "3mo")


def _brapi_url(symbol: str, range_: str, token: str) -> str:
    url = (f"https://brapi.dev/api/quote/{urllib.parse.quote(symbol)}"
           f"?range={range_}&interval=1d&fundamental=false")
    if token:
        url += f"&token={urllib.parse.quote(token)}"
    return url


def fetch_brapi_daily(ticker: str,
                      ranges: tuple[str, ...] = BRAPI_RANGES
                      ) -> list[tuple[str, float, float]]:
    """Serie diaria da B3 via brapi.dev.

    O token vem de BRAPI_TOKEN quando definido; sem ele tenta anonimo, que a
    brapi ainda serve com limites mais apertados.
    """
    import os
    symbol = ticker.replace(".SA", "").upper()
    token = os.environ.get("BRAPI_TOKEN", "").strip()
    best: list[tuple[str, float, float]] = []
    errors: list[str] = []
    for range_ in ranges:
        try:
            payload = json.loads(
                _http_get(_brapi_url(symbol, range_, token)).decode("utf-8"))
        except DataSourceError as err:
            errors.append(f"{range_}: {str(err)[-60:]}")
            continue
        results = payload.get("results") or []
        if not results:
            errors.append(f"{range_}: sem resultados")
            continue
        rows: list[tuple[str, float, float]] = []
        for point in results[0].get("historicalDataPrice") or []:
            close, stamp = point.get("close"), point.get("date")
            if close is None or stamp is None:
                continue
            date = datetime.fromtimestamp(int(stamp),
                                          tz=timezone.utc).strftime("%Y-%m-%d")
            rows.append((date, float(close), float(point.get("volume") or 0.0)))
        if len(rows) > len(best):
            best = rows
        if len(best) >= 260:      # ja chega para o momentum 12-1
            break
    if len(best) < 10:
        raise DataSourceError(f"brapi sem serie utilizavel para {symbol} "
                              f"[{'; '.join(errors[:2])}]")
    best.sort(key=lambda r: r[0])
    return best


def fetch_b3_daily(ticker: str,
                   is_benchmark: bool = False) -> list[tuple[str, float, float]]:
    """Serie diaria da B3: brapi.dev primeiro, Yahoo como alternativa.

    A brapi vem a frente porque o Yahoo passou a limitar por taxa os IPs do
    GitHub Actions, e as 50 acoes da B3 mais os benchmarks eram metade dessa
    carga. Sao servicos independentes, nao duas portas do mesmo.
    """
    from . import config
    symbol = ticker if ticker.startswith("^") else f"{ticker}.SA"
    errors: list[str] = []
    for name, call in (
            ("brapi", lambda: fetch_brapi_daily(ticker)),
            ("yahoo", lambda: fetch_yahoo_daily(
                symbol, retries=BENCHMARK_RETRIES if is_benchmark else None))):
        try:
            series = call()
        except DataSourceError as err:
            errors.append(f"{name}: {str(err)[-110:]}")
            continue
        SOURCE_TALLY[name] = SOURCE_TALLY.get(name, 0) + 1
        time.sleep(config.FETCH_DELAY_S)
        return series
    raise DataSourceError(f"Sem fonte para {ticker} — " + " | ".join(errors))


def _cdi_cache_path():
    from pathlib import Path
    return Path(__file__).resolve().parent / "state" / "cdi_cache.json"


def _load_cdi_cache() -> list[tuple[str, float]] | None:
    path = _cdi_cache_path()
    if not path.exists():
        return None
    try:
        rows = json.loads(path.read_text(encoding="utf-8"))
        return [(str(d), float(v)) for d, v in rows] or None
    except (ValueError, TypeError, OSError):
        return None


def _save_cdi_cache(rows: list[tuple[str, float]]) -> None:
    path = _cdi_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([list(r) for r in rows]), encoding="utf-8")


def _parse_sgs(payload: bytes) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    for item in json.loads(payload.decode("utf-8")):
        try:
            day, month, year = item["data"].split("/")
            rows.append((f"{year}-{month}-{day}", float(item["valor"])))
        except (KeyError, ValueError):
            continue
    rows.sort(key=lambda r: r[0])
    return rows


def fetch_bcb_cdi_daily(days_back: int = 900) -> list[tuple[str, float]]:
    """Taxa CDI diaria (% ao dia) via API SGS do Banco Central.

    O SGS e intermitente e cada uma das suas formas de consulta falha de
    maneira diferente, por isso tenta varias antes de desistir. A ordem vai da
    serie mais longa para a mais curta: uma serie curta ainda serve para render
    a caixa, mas nao chega para o obstaculo do CDI — quem decide isso e o
    chamador, com base no tamanho do que recebeu.
    """
    from . import config
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    base = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs."
            f"{config.BCB_SGS_CDI_SERIES}/dados")
    attempts = [
        f"{base}?formato=json&dataInicial={start.strftime('%d/%m/%Y')}"
        f"&dataFinal={end.strftime('%d/%m/%Y')}",
        f"{base}/ultimos/400?formato=json",
        f"{base}/ultimos/100?formato=json",
        f"{base}/ultimos/30?formato=json",
    ]
    errors: list[str] = []
    for url in attempts:
        try:
            rows = _parse_sgs(_http_get(url))
        except DataSourceError as err:
            errors.append(str(err)[:80])
            continue
        if len(rows) >= 10:
            _save_cdi_cache(rows)
            return rows
        errors.append(f"{url}: serie curta demais ({len(rows)})")

    # O CDI ja publicado nao muda, por isso a copia local e o mesmo facto, nao
    # uma estimativa. Os dias em falta simplesmente nao acumulam.
    cached = _load_cdi_cache()
    if cached:
        return cached
    raise DataSourceError("BCB SGS indisponivel e sem copia local. "
                          + " | ".join(errors[:2]))


def cdi_factor_since(rates: list[tuple[str, float]], start_date: str,
                     end_date: str) -> float:
    """Fator de acumulacao do CDI para dias uteis em (start_date, end_date]."""
    factor = 1.0
    for date, rate in rates:
        if start_date < date <= end_date:
            factor *= 1.0 + rate / 100.0
    return factor
