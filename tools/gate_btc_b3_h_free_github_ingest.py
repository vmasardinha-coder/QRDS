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
CONTINUOUS_NAME = "WINFUT_F_0_5min.csv"
EXPLICIT_RE = re.compile(r"^WIN[A-Z][0-9]{2}_F_0_5min\.csv$")
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


def download_item(session: requests.Session, item: dict) -> pd.DataFrame:
    url = item.get('download_url')
    if not url:
        raise RuntimeError(f"MISSING_DOWNLOAD_URL:{item.get('name')}")
    r = session.get(url, timeout=180)
    r.raise_for_status()
    return parse_profit_csv(r.text)


def prove_continuous_is_real_front_prices(
    session: requests.Session,
    items: list[dict],
    continuous: pd.DataFrame,
) -> dict:
    explicit_items = [x for x in items if x.get('type') == 'file' and EXPLICIT_RE.match(x.get('name', ''))]
    comparisons = []
    all_joined = []
    for item in explicit_items:
        sym = re.match(r'^(WIN[A-Z][0-9]{2})_', item['name']).group(1)
        exp = download_item(session, item)
        exp = exp[exp['source_symbol'].eq(sym)].copy()
        if exp.empty:
            comparisons.append({'file': item['name'], 'front_overlap_rows': 0})
            continue
        d = exp['timestamp'].dt.date
        exp = exp[(d >= ALLOWED_START) & (d < H1_CUTOFF)].copy()
        if exp.empty:
            comparisons.append({'file': item['name'], 'front_overlap_rows': 0})
            continue
        expected = exp['timestamp'].dt.date.map(lambda x: win_front(x).symbol)
        exp = exp[expected.eq(sym)].copy()
        if exp.empty:
            comparisons.append({'file': item['name'], 'front_overlap_rows': 0})
            continue
        j = exp.merge(
            continuous[['timestamp'] + PRICE_COLS],
            on='timestamp',
            how='inner',
            suffixes=('_explicit', '_continuous'),
        )
        if j.empty:
            comparisons.append({'file': item['name'], 'front_overlap_rows': 0})
            continue
        exact = pd.Series(True, index=j.index)
        max_abs = 0.0
        for c in PRICE_COLS:
            delta = (j[f'{c}_explicit'] - j[f'{c}_continuous']).abs()
            exact &= delta.eq(0)
            max_abs = max(max_abs, float(delta.max()))
        j['all_prices_exact'] = exact
        j['contract'] = sym
        all_joined.append(j[['timestamp', 'contract', 'all_prices_exact']])
        comparisons.append({
            'file': item['name'],
            'contract': sym,
            'front_overlap_rows': int(len(j)),
            'exact_price_rows': int(exact.sum()),
            'exact_ratio': float(exact.mean()),
            'max_abs_price_diff': max_abs,
            'sessions': int(j['timestamp'].dt.date.nunique()),
        })

    if not all_joined:
        raise RuntimeError('NO_EXPLICIT_FRONT_OVERLAP_TO_PROVE_CONTINUOUS_SERIES')
    proof = pd.concat(all_joined, ignore_index=True).drop_duplicates(['timestamp', 'contract'])
    rows = int(len(proof))
    sessions = int(proof['timestamp'].dt.date.nunique())
    exact_rows = int(proof['all_prices_exact'].sum())
    exact_ratio = float(proof['all_prices_exact'].mean())
    contracts = sorted(proof['contract'].unique().tolist())

    # This is intentionally strict: continuous history is admitted only if it is
    # empirically identical to actual explicit front-contract exports over a
    # meaningful overlap. Otherwise fail closed.
    if rows < 500 or sessions < 5 or exact_ratio < 0.999:
        raise RuntimeError(
            f'CONTINUOUS_FRONT_PRICE_PROOF_FAILED:rows={rows}:sessions={sessions}:exact={exact_ratio:.6f}'
        )
    return {
        'status': 'PASS_CONTINUOUS_REAL_FRONT_PRICE_PROOF',
        'rows_compared': rows,
        'sessions_compared': sessions,
        'exact_rows': exact_rows,
        'exact_ratio': exact_ratio,
        'contracts_compared': contracts,
        'per_file': comparisons,
    }


def build(out_csv: Path, out_meta: Path, out_report: Path) -> dict:
    s = requests.Session()
    s.headers.update({'User-Agent': 'QRDS-B3-H-Free-GitHub-Ingest/2.0'})
    items = list_source_items(s)
    continuous_item = next((x for x in items if x.get('name') == CONTINUOUS_NAME), None)
    if continuous_item is None:
        raise RuntimeError('WINFUT_M5_SOURCE_NOT_FOUND')
    x = download_item(s, continuous_item)
    x = x[x['source_symbol'].eq('WINFUT')].copy()
    d = x['timestamp'].dt.date
    x = x[(d >= ALLOWED_START) & (d < H1_CUTOFF)].copy()
    if x.empty:
        raise RuntimeError('NO_PRE_H1_CONTINUOUS_ROWS')

    proof = prove_continuous_is_real_front_prices(s, items, x)

    x['symbol'] = x['timestamp'].dt.date.map(lambda z: win_front(z).symbol)
    x = x.sort_values('timestamp', kind='mergesort').drop_duplicates(['timestamp'], keep='last').reset_index(drop=True)
    if (x['timestamp'].dt.date >= H1_CUTOFF).any():
        raise RuntimeError('H1_CUTOFF_BREACH')
    if not x['symbol'].str.match(r'^WIN[A-Z][0-9]{2}$').all():
        raise RuntimeError('NON_EXPLICIT_CAUSAL_SYMBOL')
    for c in PRICE_COLS:
        if (((x[c] / 5.0) - (x[c] / 5.0).round()).abs() > 1e-9).any():
            raise RuntimeError(f'OFF_TICK:{c}')

    x['timestamp'] = x['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    x[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']].to_csv(out_csv, index=False)
    raw = out_csv.read_bytes()
    meta = {
        'source_type': 'COMMUNITY_GITHUB_NELOGICA_PROFIT_EXPORT_CONTINUOUS_CROSSVALIDATED_TO_EXPLICIT_FRONT',
        'source_repository': SRC_REPO,
        'source_branch': SRC_BRANCH,
        'source_directory': SRC_DIR,
        'source_file': CONTINUOUS_NAME,
        'source_file_sha': continuous_item.get('sha'),
        'adjustment_mode': 'UNADJUSTED_REAL_CONTRACT_PRICES',
        'bar_minutes': 5,
        'timezone': TZ,
        'roll_policy': 'PROFIT_REAL_CONTRACT_ROLL_UNADJUSTED',
        'continuous_price_proof': proof,
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
        'rows': int(len(x)),
        'sessions': int(pd.to_datetime(x['timestamp']).dt.date.nunique()),
        'first_timestamp': x['timestamp'].iloc[0],
        'last_timestamp': x['timestamp'].iloc[-1],
        'symbols': sorted(x['symbol'].unique().tolist()),
        'continuous_price_proof': proof,
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
