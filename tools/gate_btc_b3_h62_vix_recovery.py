#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, math
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF = pd.Timestamp('2026-08-10')
THRESHOLDS = (1.0, 1.5)
HORIZONS = (60, 120)
MAPPINGS = ('same', 'opposite')
ASSETS = ('WIN', 'WDO')


def fetch_vix():
    url = 'https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv'
    r = requests.get(url, timeout=(5, 35), headers={'User-Agent': 'QRDS-research/1.0'})
    r.raise_for_status()
    raw = r.content
    z = pd.read_csv(StringIO(raw.decode('utf-8-sig')))
    cols = {c.strip().upper(): c for c in z.columns}
    if 'DATE' not in cols or 'CLOSE' not in cols:
        raise ValueError('unexpected Cboe VIX schema')
    # Cboe publishes VIX_History dates in US month/day/year semantics.
    # Do not reuse the BCB-oriented dayfirst parser.
    dates = pd.to_datetime(z[cols['DATE']], errors='coerce', dayfirst=False)
    vals = pd.to_numeric(z[cols['CLOSE']], errors='coerce')
    x = pd.DataFrame({'date': dates, 'value': vals}).dropna().sort_values('date').drop_duplicates('date')
    x = x[(x.date >= pd.Timestamp('2019-01-01')) & (x.date < CUTOFF)]
    if x.empty or not x.date.is_monotonic_increasing or x.date.duplicated().any():
        raise ValueError('invalid/empty Cboe VIX history')
    meta = {
        'name': 'VIX', 'series': 'VIX', 'provider': 'Cboe Global Markets',
        'delivery_path': 'official_csv_us_date_semantics', 'url': r.url,
        'sha256': hashlib.sha256(raw).hexdigest(), 'rows': len(x),
        'first': x.date.min().date().isoformat(), 'last': x.date.max().date().isoformat(),
    }
    return meta, x


def sample(periods, bar):
    return b.sample(periods, bar)


def coverage(x, sessions):
    d = x[['date', 'value']].sort_values('date')
    left = pd.DataFrame({'session': pd.to_datetime(sorted(sessions))}).sort_values('session')
    j = pd.merge_asof(left, d, left_on='session', right_on='date', direction='backward', allow_exact_matches=False)
    age = (j.session - j.date).dt.days
    ok = j.value.notna() & age.notna() & (age <= 5)
    return float(ok.mean()), int(ok.sum()), int(len(j)), int(age.dropna().max()) if age.notna().any() else None


def causal_signals(x, sessions):
    d = x[['date', 'value']].copy().sort_values('date')
    d['move'] = d['value'].diff()
    d['scale'] = d['move'].abs().shift(1).rolling(20, min_periods=20).median()
    d['z'] = d['move'] / d['scale']
    left = pd.DataFrame({'session': pd.to_datetime(sorted(sessions))}).sort_values('session')
    j = pd.merge_asof(left, d[['date','move','z']], left_on='session', right_on='date', direction='backward', allow_exact_matches=False)
    j['age_days'] = (j.session - j.date).dt.days
    j = j[(j.age_days >= 1) & (j.age_days <= 5)]
    return {r.session.date().isoformat(): r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def add(rows, s, g, asset, side, horizon, param, bar):
    entry = 0
    exit_i = entry + horizon // bar
    delay_entry = 1
    delay_exit = delay_entry + horizon // bar
    if exit_i >= len(g):
        return
    col = f'open_{asset}'
    gross = b.rb(side, float(g.iloc[entry][col]), float(g.iloc[exit_i][col]))
    delay = b.rb(side, float(g.iloc[delay_entry][col]), float(g.iloc[delay_exit][col])) if delay_exit < len(g) else np.nan
    if math.isfinite(gross):
        rows.append(dict(family='H62', session=s, asset=asset, side=side, param=param, horizon=horizon, gross=gross, delay=delay))


def generate(ss, bar, signals):
    rows = []
    for s, g in ss.items():
        sig = signals.get(s)
        if sig is None:
            continue
        z, mv = float(sig.z), float(sig.move)
        if not math.isfinite(z) or not math.isfinite(mv) or mv == 0:
            continue
        sign = 1 if mv > 0 else -1
        for th in THRESHOLDS:
            if abs(z) < th:
                continue
            for asset in ASSETS:
                for mapping in MAPPINGS:
                    side = sign if mapping == 'same' else -sign
                    for h in HORIZONS:
                        add(rows, s, g, asset, side, h, f'{mapping}_{th}', bar)
    return pd.DataFrame(rows)


def summarize(t):
    qualified, cells = [], []
    if t.empty:
        return {'qualified_cells': 0, 'surviving_legs': [], 'survives': False, 'qualified': []}, cells
    for (asset, param, h), g in t.groupby(['asset','param','horizon']):
        ok, reasons, m = b.metric(g, *b.COST[asset])
        cells.append(dict(family='H62', asset=asset, param=param, horizon=int(h), qualified=ok, reasons='|'.join(reasons), **m))
        if ok:
            qualified.append((asset, param, int(h)))
    legs = []
    for asset in ASSETS:
        qa = [x for x in qualified if x[0] == asset]
        if len(qa) >= 2 and (len({x[1] for x in qa}) >= 2 or len({x[2] for x in qa}) >= 2):
            legs.append(asset)
    return {'qualified_cells': len(qualified), 'surviving_legs': legs, 'survives': bool(legs),
            'qualified': sorted(f'{a}|{p}|{h}' for a,p,h in qualified)}, cells


def main(out, ledger, cells):
    ds, dcov = sample(['2024_26'], 5)
    rs, rcov = sample(['2020_22','2022_24'], 15)
    meta, x = fetch_vix()
    dcv, dn, dt, dm = coverage(x, ds)
    rcv, rn, rt, rm = coverage(x, rs)
    meta.update({'discovery_join_coverage': dcv, 'replication_join_coverage': rcv,
                 'discovery_join_n': f'{dn}/{dt}', 'replication_join_n': f'{rn}/{rt}',
                 'max_stale_days_discovery': dm, 'max_stale_days_replication': rm})
    if dcv < .90 or rcv < .90:
        raise SystemExit(f'FAIL VIX coverage below preregistered gate: discovery={dcv:.4f} replication={rcv:.4f}')
    meta['status'] = 'PASS'
    D, dc = summarize(generate(ds, 5, causal_signals(x, ds)))
    R, rc = summarize(generate(rs, 15, causal_signals(x, rs)))
    state = 'SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
    result = {
        'schema': 'gate_btc.b3.h62.vix_recovery.v1', 'family': 'H62', 'state': state,
        'cutoff_exclusive': '2026-08-10', 'source': meta, 'discovery': D, 'replication': R,
        'discovery_sync_sessions': len(ds), 'replication_sync_sessions': len(rs),
        'discovery_median_common_bar_coverage': float(np.median(dcov)) if dcov else 0,
        'replication_median_common_bar_coverage': float(np.median(rcov)) if rcov else 0,
        'h1_economics_read': False, 'survivor_partial_economics_read': False,
        'orders_generated': 0, 'real_capital_used': 0, 'engine_feed': False,
    }
    Path(out).write_text(json.dumps(result, indent=2, sort_keys=True))
    Path(ledger).write_text(json.dumps({'family':'H62','generation':'H60_H69_V1','state':state,'discovery':D,'replication':R,'source':meta,'orders':0,'capital':0,'engine_feed':False}, sort_keys=True)+'\n')
    allcells = [dict(sample='DISCOVERY', **z) for z in dc] + [dict(sample='REPLICATION', **z) for z in rc]
    pd.DataFrame(allcells).to_csv(cells, index=False)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True); p.add_argument('--ledger', required=True); p.add_argument('--cells', required=True)
    a = p.parse_args(); main(a.out, a.ledger, a.cells)
