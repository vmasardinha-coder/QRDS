"""Fontes publicas de dados de mercado (sem chave de API).

Acoes: Stooq (CSV diario). Crypto: Coinbase Exchange com fallback CoinGecko.
Todas as funcoes devolvem series diarias ordenadas por data ascendente:
lista de tuplos (date_iso: str, close: float).
"""

from __future__ import annotations

import csv
import io
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

USER_AGENT = "QRDS-trading-agent/1.0 (research; paper trading)"
RETRIES = 3
RETRY_SLEEP_S = 3.0


class DataSourceError(RuntimeError):
    pass


def _http_get(url: str, timeout: float = 30.0) -> bytes:
    last_err: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as err:
            last_err = err
            time.sleep(RETRY_SLEEP_S * (attempt + 1))
    raise DataSourceError(f"GET {url} falhou apos {RETRIES} tentativas: {last_err}")


def fetch_stooq_daily(ticker: str) -> list[tuple[str, float]]:
    """Serie diaria de fecho para um ticker dos EUA via Stooq."""
    symbol = ticker.lower().replace(".", "-") + ".us"
    raw = _http_get(f"https://stooq.com/q/d/l/?s={symbol}&i=d")
    text = raw.decode("utf-8", errors="replace")
    rows: list[tuple[str, float]] = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        try:
            close = float(row["Close"])
            date = row["Date"]
        except (KeyError, TypeError, ValueError):
            continue
        if close > 0:
            rows.append((date, close))
    if len(rows) < 10:
        raise DataSourceError(f"Stooq devolveu serie vazia/invalida para {ticker}")
    rows.sort(key=lambda r: r[0])
    return rows


def fetch_coinbase_daily(asset: str, days: int = 420) -> list[tuple[str, float]]:
    """Serie diaria de fecho (UTC) para <asset>-USD via Coinbase Exchange.

    A API limita a 300 velas por pedido; pagina em janelas de 250 dias.
    """
    product = f"{asset.upper()}-USD"
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    out: dict[str, float] = {}
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
            ts, close = int(candle[0]), float(candle[4])
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            out[date] = close
        cursor_end = cursor_start
        remaining -= span
        time.sleep(0.34)  # limite de taxa publico da Coinbase
    if len(out) < 10:
        raise DataSourceError(f"Coinbase devolveu serie vazia para {product}")
    return sorted(out.items())


def fetch_coingecko_daily(coin_id: str, days: int = 365) -> list[tuple[str, float]]:
    """Fallback: serie diaria via CoinGecko (free tier)."""
    url = (
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        f"?vs_currency=usd&days={days}"
    )
    data = json.loads(_http_get(url).decode("utf-8"))
    prices = data.get("prices")
    if not prices:
        raise DataSourceError(f"CoinGecko devolveu serie vazia para {coin_id}")
    out: dict[str, float] = {}
    for ms, price in prices:
        date = datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        out[date] = float(price)
    return sorted(out.items())


def fetch_crypto_daily(asset: str, coingecko_id: str) -> list[tuple[str, float]]:
    """Coinbase como fonte primaria, CoinGecko como fallback."""
    try:
        return fetch_coinbase_daily(asset)
    except DataSourceError:
        return fetch_coingecko_daily(coingecko_id)
