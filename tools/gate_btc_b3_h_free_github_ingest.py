#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from gate_btc_b3_h_win_contract_manifest import ALLOWED_START, H1_CUTOFF, win_front

SRC_REPO = "wesleyzilva/tradetech"
SRC_BRANCH = "main"
SRC_DIR = "CandlesHistoryDatas/2024_26"
API_DIR = f"https://api.github.com/repos/{SRC_REPO}/contents/{SRC_DIR}?ref={SRC_BRANCH}"
CONTINUOUS_NAME = "WINFUT_F_0_5min.csv"
TZ = "America/Sao_Paulo"
PRICE_COLS = ['open', 'high', 'low', 'close']


def br_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='raise',
    )


def parse_profit_csv(text: str) -> pd.DataFrame:
    df = pd.read_csv(StringIO(text), sep=';', dtype=str)
    cols = {c.lower().strip(): c for c in df.columns}
    need = ['ativo', 'data', 'hora', 'abertura', 'máximo', 'mínimo', 'fechamento', 'quantidade']
    missing = [x for x in need if x not in cols]
    if missing:
        raise RuntimeError(f"SOURCE_SCHEMA_MISSING:{missing}")
    out = pd.DataFrame()
    out['source_symbol'] = df[cols['ativo']].str.strip().str.upper()
    out['timestamp'] = pd.to_datetime(
        df[cols['data']].str.strip() + ' ' + df[cols['hora']].str.strip(),
        dayfirst=True,
        errors='raise',
    )
    for src, dst in [('abertura', 'open'), ('máximo', 'high'), ('mínimo', 'low'), ('fechamento', 'close')]:
        out[dst] = br_num(df[cols[src]])
    out['volume'] = br_num(df[cols['quantidade']])
    return out


def list_source_items(session: requests.Session) -> list[dict]:
    r = session.get(API_DIR, timeout=60)
    r.raise_for_status()
    items = r.json()
    if not isinstance(items, list):
        raise RuntimeError('SOURCE_DIRECTORY_RESPONSE_NOT_LIST')
    return items


def build(out_csv: Path, out_meta: Path, out_report: Path) -> dict:
    s = requests.Session()
    s.headers.update({'User-Agent': 'QRDS-B3-H-Free-GitHub-Ingest/3.1'})
    items = list_source_items(s)
    item = next((x for x in items if x.get('name') == CONTINUOUS_NAME), None)
    if item is None or not item.get('download_url'):
        raise RuntimeError('WINFUT_M5_SOURCE_NOT_FOUND')
    r = s.get(item['download_url'], timeout=180)
    r.raise_for_status()
    x = parse_profit_csv(r.text)
    x = x[x['source_symbol'].eq('WINFUT')].copy()
    d = x['timestamp'].dt.date
    x = x[(d >= ALLOWED_START) & (d < H1_CUTOFF)].copy()
    if x.empty:
        raise RuntimeError('NO_PRE_H1_CONTINUOUS_ROWS')

    # This source is used only for same-session, translation-invariant families.
    # No absolute-level or cross-roll inference is permitted. We attach the
    # causal front-contract label by calendar only for session bookkeeping.
    x['symbol'] = x['timestamp'].dt.date.map(lambda z: win_front(z).symbol)
    x = x.sort_values('timestamp', kind='mergesort').drop_duplicates(['timestamp'], keep='last').reset_index(drop=True)
    if (x['timestamp'].dt.date >= H1_CUTOFF).any():
        raise RuntimeError('H1_CUTOFF_BREACH')

    off_grid = {}
    for c in PRICE_COLS:
        ratio = x[c] / 5.0
        off = (ratio - ratio.round()).abs() > 1e-9
        off_grid[c] = int(off.sum())

    x['timestamp'] = x['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    x[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']].to_csv(out_csv, index=False)
    raw = out_csv.read_bytes()
    meta = {
        'source_type': 'COMMUNITY_GITHUB_NELOGICA_PROFIT_WINFUT_EXPORT',
        'source_repository': SRC_REPO,
        'source_branch': SRC_BRANCH,
        'source_directory': SRC_DIR,
        'source_file': CONTINUOUS_NAME,
        'source_file_sha': item.get('sha'),
        'source_documentation': 'CandlesHistoryDatas/DadosCandlesBacktest.md',
        'adjustment_mode': 'CONTINUOUS_INTRADAY_TRANSLATION_INVARIANT_ONLY',
        'research_scope': 'INTRADAY_TRANSLATION_INVARIANT_FAMILIES_ONLY',
        'absolute_level_research_allowed': False,
        'fixed_point_economics_allowed': False,
        'off_tick_rows_by_price_column': off_grid,
        'bar_minutes': 5,
        'timezone': TZ,
        'roll_policy': 'PROFIT_CONTINUOUS_INTRADAY_ONLY',
        'research_only': True,
        'shadow_only': True,
        'not_approved': True,
        'h1_cutoff_exclusive': H1_CUTOFF.isoformat(),
        'h1_economics_read': False,
        'orders': 0,
        'real_capital': 0,
        'sha256': hashlib.sha256(raw).hexdigest(),
    }
    out_meta.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    report = {
        'status': 'PASS_SOURCE_INGEST_INTRADAY_ONLY',
        'rows': int(len(x)),
        'sessions': int(pd.to_datetime(x['timestamp']).dt.date.nunique()),
        'first_timestamp': x['timestamp'].iloc[0],
        'last_timestamp': x['timestamp'].iloc[-1],
        'symbols': sorted(x['symbol'].unique().tolist()),
        'research_scope': meta['research_scope'],
        'absolute_level_research_allowed': False,
        'fixed_point_economics_allowed': False,
        'off_tick_rows_by_price_column': off_grid,
        'research_only': True,
        'h1_economics_read': False,
        'orders': 0,
        'real_capital': 0,
    }
    out_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-csv', default='artifacts/b3_h_nextgen/WIN_M5_PRE_H1_GITHUB.csv')
    ap.add_argument('--out-meta', default='artifacts/b3_h_nextgen/WIN_M5_PRE_H1_GITHUB.metadata.json')
    ap.add_argument('--out-report', default='artifacts/b3_h_nextgen/WIN_M5_PRE_H1_GITHUB.report.json')
    a = ap.parse_args()
    build(Path(a.out_csv), Path(a.out_meta), Path(a.out_report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
