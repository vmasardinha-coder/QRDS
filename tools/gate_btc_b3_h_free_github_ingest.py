#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from gate_btc_b3_h_win_contract_manifest import ALLOWED_START, H1_CUTOFF, win_front

SRC_REPO = "wesleyzilva/tradetech"
SRC_BRANCH = "main"
SRC_DIR = "CandlesHistoryDatas/2024_26"
API_DIR = f"https://api.github.com/repos/{SRC_REPO}/contents/{SRC_DIR}?ref={SRC_BRANCH}"
FILE_RE = re.compile(r"^WIN[A-Z][0-9]{2}_F_0_5min\.csv$")
TZ = "America/Sao_Paulo"


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
    out['symbol'] = df[cols['ativo']].str.strip().str.upper()
    out['timestamp'] = pd.to_datetime(
        df[cols['data']].str.strip() + ' ' + df[cols['hora']].str.strip(),
        dayfirst=True,
        errors='raise',
    )
    for src, dst in [('abertura', 'open'), ('máximo', 'high'), ('mínimo', 'low'), ('fechamento', 'close')]:
        out[dst] = br_num(df[cols[src]])
    out['volume'] = br_num(df[cols['quantidade']])
    return out


def fetch_sources(session: requests.Session) -> list[dict]:
    r = session.get(API_DIR, timeout=60)
    r.raise_for_status()
    items = r.json()
    files = [x for x in items if x.get('type') == 'file' and FILE_RE.match(x.get('name', ''))]
    if not files:
        raise RuntimeError('NO_EXPLICIT_WIN_M5_CONTRACT_FILES_FOUND')
    return files


def build(out_csv: Path, out_meta: Path, out_report: Path) -> dict:
    s = requests.Session()
    s.headers.update({'User-Agent': 'QRDS-B3-H-Free-GitHub-Ingest/1.0'})
    files = fetch_sources(s)
    kept = []
    file_report = []
    for item in files:
        url = item.get('download_url')
        if not url:
            raise RuntimeError(f"MISSING_DOWNLOAD_URL:{item['name']}")
        r = s.get(url, timeout=120)
        r.raise_for_status()
        df = parse_profit_csv(r.text)
        sym = re.match(r'^(WIN[A-Z][0-9]{2})_', item['name']).group(1)
        df = df[df['symbol'].eq(sym)].copy()
        d = df['timestamp'].dt.date
        df = df[(d >= ALLOWED_START) & (d < H1_CUTOFF)].copy()
        if not df.empty:
            expected = df['timestamp'].dt.date.map(lambda x: win_front(x).symbol)
            df = df[df['symbol'].eq(expected)].copy()
        kept.append(df)
        file_report.append({'name': item['name'], 'sha': item.get('sha'), 'rows_front_kept': int(len(df))})

    x = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame()
    if x.empty:
        raise RuntimeError('NO_CAUSAL_FRONT_CONTRACT_ROWS_AFTER_FILTER')
    x = x.sort_values('timestamp', kind='mergesort').drop_duplicates(['timestamp'], keep='last').reset_index(drop=True)
    if (x['timestamp'].dt.date >= H1_CUTOFF).any():
        raise RuntimeError('H1_CUTOFF_BREACH')
    if not x['symbol'].str.match(r'^WIN[A-Z][0-9]{2}$').all():
        raise RuntimeError('NON_EXPLICIT_SYMBOL')
    for c in ['open', 'high', 'low', 'close']:
        if (((x[c] / 5.0) - (x[c] / 5.0).round()).abs() > 1e-9).any():
            raise RuntimeError(f'OFF_TICK:{c}')

    x['timestamp'] = x['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    x[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']].to_csv(out_csv, index=False)
    raw = out_csv.read_bytes()
    meta = {
        'source_type': 'COMMUNITY_GITHUB_NELOGICA_PROFIT_EXPORT_EXPLICIT_CONTRACTS',
        'source_repository': SRC_REPO,
        'source_branch': SRC_BRANCH,
        'source_directory': SRC_DIR,
        'adjustment_mode': 'EXPLICIT_CONTRACTS_NO_BACK_ADJUSTMENT',
        'bar_minutes': 5,
        'timezone': TZ,
        'roll_policy': 'EXPLICIT_REAL_CONTRACT_STITCH',
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
        'status': 'PASS_SOURCE_INGEST_ONLY',
        'rows': len(x),
        'sessions': pd.to_datetime(x['timestamp']).dt.date.nunique(),
        'first_timestamp': x['timestamp'].iloc[0],
        'last_timestamp': x['timestamp'].iloc[-1],
        'symbols': sorted(x['symbol'].unique().tolist()),
        'files': file_report,
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
