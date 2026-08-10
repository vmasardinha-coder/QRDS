"""Fontes publicas de dados de mercado (sem chave de API).

Acoes: Stooq (CSV diario) com fallback Yahoo. Crypto: Coinbase Exchange com
fallback CoinGecko. Acoes B3: Yahoo (sufixo .SA). CDI: API SGS do Banco Central.

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

USER_AGENT = "QRDS-trading-agent/1.0 (research; paper trading)"
RETRIES = 3
RETRY_SLEEP_S = 3.0


class DataSourceError(RuntimeError):
    pass


# 4xx que significam "nao existe / nao autorizado": repetir nao muda o
# resultado e, com universos grandes, custa dezenas de minutos por ciclo.
PERMANENT_HTTP = {400, 401, 403, 404, 410, 422}


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as err:
            last_err = err
            if err.code in PERMANENT_HTTP:
                raise DataSourceError(f"GET {url}: HTTP {err.code} (definitivo)")
            time.sleep(RETRY_SLEEP_S * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            last_err = err
            time.sleep(RETRY_SLEEP_S * (attempt + 1))
    raise DataSourceError(f"GET {url} falhou apos {RETRIES} tentativas: {last_err}")


def fetch_stooq_daily(ticker: str) -> list[tuple[str, float, float]]:
    """Serie diaria de fecho para um ticker dos EUA via Stooq."""
    symbol = ticker.lower().replace(".", "-") + ".us"
    raw = _http_get(f"https://stooq.com/q/d/l/?s={symbol}&i=d")
    text = raw.decode("utf-8", errors="replace")
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
        raise DataSourceError(f"Stooq devolveu serie vazia/invalida para {ticker}")
    rows.sort(key=lambda r: r[0])
    return rows


def fetch_yahoo_daily(ticker: str) -> list[tuple[str, float, float]]:
    """Serie diaria de fecho via API de chart do Yahoo Finance (sem chave)."""
    symbol = ticker.upper()
    # tickers dos EUA usam '-' em vez de '.' (BRK.B); indices (^BVSP) e
    # tickers da B3 (.SA) ficam como estao
    if not (symbol.startswith("^") or symbol.endswith(".SA")):
        symbol = symbol.replace(".", "-")
    symbol = urllib.parse.quote(symbol)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?range=2y&interval=1d&events=div%2Csplit"
    )
    data = json.loads(_http_get(url).decode("utf-8"))
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


def fetch_equity_daily(ticker: str) -> list[tuple[str, float, float]]:
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
            time.sleep(config.FETCH_DELAY_S)
            return series
        except DataSourceError:
            _STOOQ_CONSECUTIVE_FAILURES += 1
    series = fetch_yahoo_daily(ticker)
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


def fetch_crypto_daily(asset: str, coingecko_id: str) -> list[tuple[str, float, float]]:
    """Coinbase como fonte primaria, CoinGecko como fallback."""
    try:
        return fetch_coinbase_daily(asset)
    except DataSourceError:
        return fetch_coingecko_daily(coingecko_id)

def fetch_b3_daily(ticker: str) -> list[tuple[str, float, float]]:
    """Serie diaria de fecho para um ticker da B3 via Yahoo (sufixo .SA)."""
    from . import config
    symbol = ticker if ticker.startswith("^") else f"{ticker}.SA"
    series = fetch_yahoo_daily(symbol)
    time.sleep(config.FETCH_DELAY_S)
    return series


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


def fetch_bcb_cdi_daily(days_back: int = 900) -> list[tuple[str, float]]:
    """Taxa CDI diaria (% ao dia) via API SGS do Banco Central do Brasil.

    Usa consulta por intervalo de datas (o endpoint 'ultimos/N' tem limites
    baixos e devolve 400 para N grandes).
    """
    from . import config
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    url = (
        f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{config.BCB_SGS_CDI_SERIES}"
        f"/dados?formato=json"
        f"&dataInicial={start.strftime('%d/%m/%Y')}"
        f"&dataFinal={end.strftime('%d/%m/%Y')}"
    )
    try:
        data = json.loads(_http_get(url).decode("utf-8"))
    except DataSourceError:
        # O SGS do Banco Central tem indisponibilidades passageiras (502). O CDI
        # ja publicado nao muda, por isso a copia local e o mesmo facto, nao uma
        # estimativa. Os dias em falta simplesmente nao acumulam ate a fonte
        # voltar — nada e inventado.
        cached = _load_cdi_cache()
        if cached:
            return cached
        raise

    rows: list[tuple[str, float]] = []
    for item in data:
        try:
            day, month, year = item["data"].split("/")
            rows.append((f"{year}-{month}-{day}", float(item["valor"])))
        except (KeyError, ValueError):
            continue
    if len(rows) < 10:
        cached = _load_cdi_cache()
        if cached:
            return cached
        raise DataSourceError("BCB devolveu serie CDI vazia/invalida")
    rows.sort(key=lambda r: r[0])
    _save_cdi_cache(rows)
    return rows


def cdi_factor_since(rates: list[tuple[str, float]], start_date: str,
                     end_date: str) -> float:
    """Fator de acumulacao do CDI para dias uteis em (start_date, end_date]."""
    factor = 1.0
    for date, rate in rates:
        if start_date < date <= end_date:
            factor *= 1.0 + rate / 100.0
    return factor
