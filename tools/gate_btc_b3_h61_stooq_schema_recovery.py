#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from io import StringIO

import pandas as pd
import requests

import gate_btc_b3_h61_public_mirror_recovery as base


def _parse_market_csv(raw: bytes) -> pd.DataFrame:
    text = raw.decode('utf-8-sig', errors='replace')
    attempts = []
    for sep in (',', ';', '\t'):
        try:
            z = pd.read_csv(StringIO(text), sep=sep)
        except Exception as exc:
            attempts.append(f'{sep!r}:{type(exc).__name__}')
            continue
        normalized = {str(c).strip().lstrip('\ufeff').lower(): c for c in z.columns}
        if 'date' in normalized and 'close' in normalized:
            return z.rename(columns={normalized['date']: 'Date', normalized['close']: 'Close'})
    first = text.splitlines()[0][:240] if text.splitlines() else ''
    raise ValueError(f"Stooq payload is not recognized market CSV; first_line={first!r}; parse_attempts={attempts}")


def fetch_stooq_mechanical():
    url = 'https://stooq.com/q/d/l/?s=%5Espx&i=d&d1=20190101&d2=20260809'
    r = requests.get(url, timeout=(10, 60), headers={'User-Agent': 'Mozilla/5.0 QRDS-research/1.0', 'Accept': 'text/csv,text/plain,*/*'})
    r.raise_for_status()
    raw = r.content
    z = _parse_market_csv(raw)
    x = z[['Date', 'Close']].rename(columns={'Date': 'date', 'Close': 'value'})
    x['date'] = pd.to_datetime(x.date, errors='coerce')
    x['value'] = pd.to_numeric(x.value, errors='coerce')
    x = x.dropna().sort_values('date').drop_duplicates('date')
    x = x[(x.date >= pd.Timestamp('2019-01-01')) & (x.date < base.CUTOFF)]
    if x.empty or x.date.duplicated().any() or not x.date.is_monotonic_increasing:
        raise ValueError('invalid normalized Stooq series')
    meta = {
        'provider': 'Stooq',
        'symbol': '^SPX',
        'instrument': 'S&P 500 cash price index',
        'url': r.url,
        'sha256': hashlib.sha256(raw).hexdigest(),
        'content_type': r.headers.get('content-type'),
        'rows': len(x),
        'first': x.date.min().date().isoformat(),
        'last': x.date.max().date().isoformat(),
        'parser': 'mechanical_case_bom_whitespace_delimiter_normalization_v1',
    }
    return meta, x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--cells', required=True)
    ap.add_argument('--ledger', required=True)
    a = ap.parse_args()
    base.fetch_stooq = fetch_stooq_mechanical
    base.main(a.out, a.cells, a.ledger)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
