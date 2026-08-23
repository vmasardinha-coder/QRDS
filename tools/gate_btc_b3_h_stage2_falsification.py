#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

H1_CUTOFF = pd.Timestamp('2026-08-10', tz='America/Sao_Paulo')
COSTS_BPS = (1.0, 2.0, 3.0)
REFERENCE_COST_BPS = 2.0
STRESS_COST_BPS = 3.0
MIN_TRADES = 60
MIN_SIDE_TRADES = 15
MIN_BUCKET_TRADES = 15
MIN_NET_EDGE_BPS = 0.25
MAX_TOP5_POSITIVE_SHARE = 0.40
MIN_QUALIFIED_CELLS = 3
LOOKBACKS = (15, 30, 60)
HORIZONS = (30, 60, 120)
H2_MULTIPLES = (0.25, 0.50, 0.75)
PRIORITY = ('H4', 'H2', 'H3')
MAX_ACTIVATED = 2


@dataclass(frozen=True)
class Trade:
    family: str
    session: str
    side: int
    lookback: int
    horizon: int
    trigger: float | None
    entry_ts: str
    exit_ts: str
    gross_bps: float
    delayed_gross_bps: float | None


def half_bucket(session: str) -> str:
    d = pd.Timestamp(session)
    return f"{d.year}H{1 if d.month <= 6 else 2}"


def _load(csv_path: Path, metadata_path: Path) -> tuple[pd.DataFrame, dict]:
    meta = json.loads(metadata_path.read_text(encoding='utf-8'))
    if meta.get('research_scope') != 'INTRADAY_TRANSLATION_INVARIANT_FAMILIES_ONLY':
        raise RuntimeError('STAGE2_REQUIRES_INTRADAY_TRANSLATION_INVARIANT_SCOPE')
    if meta.get('absolute_level_research_allowed') is not False:
        raise RuntimeError('ABSOLUTE_LEVEL_SCOPE_MUST_BE_FALSE')
    if meta.get('h1_economics_read') is not False:
        raise RuntimeError('H1_ECONOMICS_BOUNDARY_BREACH')
    df = pd.read_csv(csv_path)
    needed = {'timestamp','open','high','low','close','volume','symbol'}
    if not needed.issubset(df.columns):
        raise RuntimeError(f'SCHEMA_MISSING:{sorted(needed-set(df.columns))}')
    ts = pd.to_datetime(df['timestamp'], errors='raise')
    if getattr(ts.dt, 'tz', None) is None:
        ts = ts.dt.tz_localize('America/Sao_Paulo')
    else:
        ts = ts.dt.tz_convert('America/Sao_Paulo')
    df['timestamp'] = ts
    if (df['timestamp'] >= H1_CUTOFF).any():
        raise RuntimeError('H1_CUTOFF_BREACH')
    for c in ['open','high','low','close','volume']:
        df[c] = pd.to_numeric(df[c], errors='raise')
    df = df.sort_values('timestamp', kind='mergesort').reset_index(drop=True)
    df['session'] = df['timestamp'].dt.date.astype(str)
    return df, meta


def _complete_opening_sessions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for session, g0 in df.groupby('session', sort=True):
        g = g0.sort_values('timestamp').reset_index(drop=True)
        t0 = g.loc[0, 'timestamp']
        if (t0.hour, t0.minute) != (9, 0):
            continue
        delta = g['timestamp'].diff().dropna().dt.total_seconds()
        if not delta.empty and (delta != 300).any():
            continue
        if len(g) < 30:
            continue
        out[session] = g
    return out


def _trade_return(side: int, entry: float, exit_: float) -> float:
    if entry <= 0 or exit_ <= 0:
        return float('nan')
    return float(side * (exit_ / entry - 1.0) * 10000.0)


def _fixed_horizon_trade(
    family: str, session: str, g: pd.DataFrame, side: int,
    signal_idx: int, lookback: int, horizon: int, trigger: float | None,
) -> Trade | None:
    entry_idx = signal_idx + 1
    bars = horizon // 5
    exit_idx = entry_idx + bars
    delayed_entry_idx = entry_idx + 1
    delayed_exit_idx = delayed_entry_idx + bars
    if exit_idx >= len(g):
        return None
    entry = float(g.loc[entry_idx, 'open'])
    exit_ = float(g.loc[exit_idx, 'open'])
    gross = _trade_return(side, entry, exit_)
    delayed = None
    if delayed_exit_idx < len(g):
        delayed = _trade_return(side, float(g.loc[delayed_entry_idx, 'open']), float(g.loc[delayed_exit_idx, 'open']))
    if not math.isfinite(gross):
        return None
    return Trade(
        family=family, session=session, side=side, lookback=lookback, horizon=horizon,
        trigger=trigger, entry_ts=g.loc[entry_idx, 'timestamp'].isoformat(),
        exit_ts=g.loc[exit_idx, 'timestamp'].isoformat(), gross_bps=gross,
        delayed_gross_bps=delayed if delayed is None or math.isfinite(delayed) else None,
    )


def make_h4(sessions: dict[str, pd.DataFrame]) -> list[Trade]:
    trades: list[Trade] = []
    for session, g in sessions.items():
        session_open = float(g.loc[0, 'open'])
        for lookback in LOOKBACKS:
            n = lookback // 5
            signal_idx = n - 1
            if signal_idx >= len(g):
                continue
            signal_close = float(g.loc[signal_idx, 'close'])
            side = 1 if signal_close > session_open else -1 if signal_close < session_open else 0
            if side == 0:
                continue
            for horizon in HORIZONS:
                t = _fixed_horizon_trade('H4', session, g, side, signal_idx, lookback, horizon, None)
                if t:
                    trades.append(t)
    return trades


def trailing_ranges(sessions: dict[str, pd.DataFrame]) -> dict[str, float | None]:
    keys = sorted(sessions)
    history: list[float] = []
    out: dict[str, float | None] = {}
    for session in keys:
        out[session] = float(np.median(history[-20:])) if len(history) >= 20 else None
        g = sessions[session]
        op = float(g.loc[0, 'open'])
        rng = float((g['high'].max() - g['low'].min()) / op) if op > 0 else float('nan')
        if math.isfinite(rng) and rng > 0:
            history.append(rng)
    return out


def make_h2(sessions: dict[str, pd.DataFrame]) -> list[Trade]:
    med = trailing_ranges(sessions)
    trades: list[Trade] = []
    for session, g in sessions.items():
        scale = med.get(session)
        if not scale:
            continue
        session_open = float(g.loc[0, 'open'])
        for lookback in LOOKBACKS:
            signal_idx = lookback // 5 - 1
            signal_close = float(g.loc[signal_idx, 'close'])
            displacement = signal_close / session_open - 1.0
            for mult in H2_MULTIPLES:
                if abs(displacement) < mult * scale:
                    continue
                side = -1 if displacement > 0 else 1 if displacement < 0 else 0
                if side == 0:
                    continue
                for horizon in HORIZONS:
                    t = _fixed_horizon_trade('H2', session, g, side, signal_idx, lookback, horizon, mult)
                    if t:
                        trades.append(t)
    return trades


def make_h3(sessions: dict[str, pd.DataFrame]) -> list[Trade]:
    trades: list[Trade] = []
    for session, g in sessions.items():
        for lookback in LOOKBACKS:
            n = lookback // 5
            opening = g.iloc[:n]
            hi = float(opening['high'].max())
            lo = float(opening['low'].min())
            signal_idx = None
            side = 0
            for i in range(n, len(g)-1):
                c = float(g.loc[i, 'close'])
                if c > hi:
                    signal_idx, side = i, 1
                    break
                if c < lo:
                    signal_idx, side = i, -1
                    break
            if signal_idx is None:
                continue
            for horizon in HORIZONS:
                t = _fixed_horizon_trade('H3', session, g, side, signal_idx, lookback, horizon, None)
                if t:
                    trades.append(t)
    return trades


def _metric_group(g: pd.DataFrame) -> dict:
    gross = g['gross_bps'].astype(float)
    delayed = g['delayed_gross_bps'].dropna().astype(float)
    by_cost = {str(c): float((gross-c).mean()) for c in COSTS_BPS}
    side_metrics = {}
    for side, sg in g.groupby('side'):
        label = 'LONG' if int(side) == 1 else 'SHORT'
        side_metrics[label] = {
            'trades': int(len(sg)),
            'net_mean_bps_at_2': float((sg['gross_bps']-REFERENCE_COST_BPS).mean()),
        }
    bucket_metrics = {}
    gg = g.copy()
    gg['half'] = gg['session'].map(half_bucket)
    for b, bg in gg.groupby('half'):
        bucket_metrics[b] = {
            'trades': int(len(bg)),
            'net_mean_bps_at_2': float((bg['gross_bps']-REFERENCE_COST_BPS).mean()),
        }
    positive = gross[gross > 0].sort_values(ascending=False)
    positive_sum = float(positive.sum())
    top5_share = float(positive.head(5).sum()/positive_sum) if positive_sum > 0 else 1.0
    return {
        'trades': int(len(g)),
        'gross_mean_bps': float(gross.mean()),
        'gross_median_bps': float(gross.median()),
        'net_mean_bps_by_roundtrip_cost': by_cost,
        'delayed_net_mean_bps_at_2': float((delayed-REFERENCE_COST_BPS).mean()) if len(delayed) else None,
        'delayed_trades': int(len(delayed)),
        'side_metrics': side_metrics,
        'calendar_half_metrics': bucket_metrics,
        'top5_positive_gross_share': top5_share,
    }


def _qualify(m: dict) -> tuple[bool, list[str]]:
    reasons = []
    if m['trades'] < MIN_TRADES:
        reasons.append('MIN_TRADES')
    if m['net_mean_bps_by_roundtrip_cost'][str(REFERENCE_COST_BPS)] <= MIN_NET_EDGE_BPS:
        reasons.append('REFERENCE_COST_EDGE')
    if m['net_mean_bps_by_roundtrip_cost'][str(STRESS_COST_BPS)] <= 0:
        reasons.append('STRESS_COST')
    if m['delayed_trades'] < MIN_TRADES or m['delayed_net_mean_bps_at_2'] is None or m['delayed_net_mean_bps_at_2'] <= 0:
        reasons.append('DELAYED_ENTRY')
    sides = m['side_metrics']
    if set(sides) != {'LONG','SHORT'}:
        reasons.append('SIDE_COVERAGE')
    else:
        for sm in sides.values():
            if sm['trades'] < MIN_SIDE_TRADES or sm['net_mean_bps_at_2'] <= 0:
                reasons.append('SIDE_STABILITY')
                break
    eligible_buckets = [b for b in m['calendar_half_metrics'].values() if b['trades'] >= MIN_BUCKET_TRADES]
    if len(eligible_buckets) < 2 or any(b['net_mean_bps_at_2'] <= 0 for b in eligible_buckets):
        reasons.append('CALENDAR_HALF_STABILITY')
    if m['top5_positive_gross_share'] > MAX_TOP5_POSITIVE_SHARE:
        reasons.append('CONCENTRATION')
    return not reasons, reasons


def summarize(trades: list[Trade], family: str) -> tuple[list[dict], dict]:
    if not trades:
        return [], {'family': family, 'survives': False, 'qualified_cells': 0, 'reason': 'NO_TRADES'}
    df = pd.DataFrame([t.__dict__ for t in trades])
    keys = ['lookback','horizon'] + (['trigger'] if family == 'H2' else [])
    cells = []
    qualified = []
    for vals, g in df.groupby(keys, dropna=False, sort=True):
        if not isinstance(vals, tuple):
            vals = (vals,)
        params = dict(zip(keys, vals))
        if 'trigger' in params and pd.isna(params['trigger']):
            params['trigger'] = None
        m = _metric_group(g)
        ok, reasons = _qualify(m)
        row = {'family': family, 'params': params, 'qualified': ok, 'rejection_reasons': reasons, 'metrics': m}
        cells.append(row)
        if ok:
            qualified.append(row)
    lbs = {int(x['params']['lookback']) for x in qualified}
    hrs = {int(x['params']['horizon']) for x in qualified}
    stable = len(qualified) >= MIN_QUALIFIED_CELLS and len(lbs) >= 2 and len(hrs) >= 2
    family_summary = {
        'family': family,
        'survives': bool(stable),
        'qualified_cells': len(qualified),
        'qualified_lookbacks': sorted(lbs),
        'qualified_horizons': sorted(hrs),
        'reason': 'PASS_NEIGHBOR_STABILITY' if stable else 'FAIL_NEIGHBOR_STABILITY',
    }
    if stable:
        # Select a simple central rule, not the best historical performer.
        def simplicity(r: dict):
            p = r['params']
            trig_pen = abs(float(p.get('trigger') or 0.5)-0.5)*100 if family == 'H2' else 0
            return (abs(int(p['lookback'])-30) + abs(int(p['horizon'])-60)/2 + trig_pen,
                    int(p['lookback']), int(p['horizon']), float(p.get('trigger') or 0.0))
        chosen = sorted(qualified, key=simplicity)[0]
        family_summary['frozen_candidate'] = chosen['params']
        family_summary['selection_rule'] = 'CENTRAL_SIMPLEST_QUALIFIED_NOT_BEST_PERFORMANCE'
    return cells, family_summary


def run(csv_path: Path, metadata_path: Path, out_json: Path, out_cells_csv: Path) -> dict:
    df, meta = _load(csv_path, metadata_path)
    sessions = _complete_opening_sessions(df)
    h4 = make_h4(sessions)
    h2 = make_h2(sessions)
    h3 = make_h3(sessions)
    all_cells = []
    summaries = []
    for family, trades in [('H4',h4),('H2',h2),('H3',h3)]:
        cells, summary = summarize(trades, family)
        all_cells.extend(cells)
        summaries.append(summary)
    surviving = {s['family']: s for s in summaries if s['survives']}
    activated = []
    for fam in PRIORITY:
        if fam in surviving and len(activated) < MAX_ACTIVATED:
            s = surviving[fam]
            activated.append({
                'family': fam,
                'version': f'{fam}_NEXTGEN_PROSPECTIVE_V1',
                'params': s['frozen_candidate'],
                'status': 'ACTIVATE_PROSPECTIVE_RESEARCH_ONLY',
                'activation_capital': 0,
                'orders': 0,
                'raw_tradable_price_confirmation_required_before_any_execution': True,
            })
    flat_cells = []
    for c in all_cells:
        p, m = c['params'], c['metrics']
        flat_cells.append({
            'family': c['family'], 'lookback': p.get('lookback'), 'horizon': p.get('horizon'),
            'trigger': p.get('trigger'), 'qualified': c['qualified'],
            'rejection_reasons': '|'.join(c['rejection_reasons']), 'trades': m['trades'],
            'gross_mean_bps': m['gross_mean_bps'], 'net_mean_bps_cost2': m['net_mean_bps_by_roundtrip_cost'][str(REFERENCE_COST_BPS)],
            'net_mean_bps_cost3': m['net_mean_bps_by_roundtrip_cost'][str(STRESS_COST_BPS)],
            'delayed_net_mean_bps_cost2': m['delayed_net_mean_bps_at_2'],
            'top5_positive_gross_share': m['top5_positive_gross_share'],
        })
    out_cells_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(flat_cells).to_csv(out_cells_csv, index=False)
    payload = {
        'schema': 'gate_btc.b3.h_nextgen.stage2_falsification.v1',
        'status': 'PASS_RESEARCH_COMPLETE_NO_LIVE_APPROVAL',
        'source_adjustment_mode': meta['adjustment_mode'],
        'research_scope': meta['research_scope'],
        'sessions_admitted': len(sessions),
        'first_session': min(sessions) if sessions else None,
        'last_session': max(sessions) if sessions else None,
        'h1_cutoff_exclusive': '2026-08-10',
        'h1_economics_read': False,
        'research_only': True,
        'shadow_only': True,
        'not_approved_for_trading': True,
        'orders': 0,
        'real_capital': 0,
        'fixed_point_economics_used': False,
        'cost_model': {'unit':'roundtrip_bps','grid':list(COSTS_BPS),'reference':REFERENCE_COST_BPS,'stress':STRESS_COST_BPS},
        'acceptance_criteria': {
            'min_trades': MIN_TRADES, 'min_side_trades': MIN_SIDE_TRADES,
            'min_bucket_trades': MIN_BUCKET_TRADES, 'min_net_edge_bps_at_reference_cost': MIN_NET_EDGE_BPS,
            'stress_cost_must_remain_positive': True, 'delayed_entry_must_remain_positive': True,
            'both_sides_must_be_positive': True, 'all_eligible_calendar_halves_must_be_positive': True,
            'max_top5_positive_gross_share': MAX_TOP5_POSITIVE_SHARE,
            'min_qualified_neighbor_cells': MIN_QUALIFIED_CELLS,
            'family_must_span_two_lookbacks_and_two_horizons': True,
            'max_activated_families': MAX_ACTIVATED,
            'activation_priority': list(PRIORITY),
        },
        'family_summaries': summaries,
        'activated_prospective_candidates': activated,
        'h5_status': 'ELIGIBLE_FOR_SEPARATE_PREREGISTERED_ROBUSTNESS_TEST' if any(x['family'] in {'H2','H4'} for x in activated) else 'NOT_ELIGIBLE_NO_UNCONDITIONED_H2_H4_SURVIVOR',
        'cells': all_cells,
    }
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: payload[k] for k in ['status','sessions_admitted','family_summaries','activated_prospective_candidates','h5_status']}, ensure_ascii=False))
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', required=True)
    ap.add_argument('--metadata', required=True)
    ap.add_argument('--out-json', default='artifacts/b3_h_nextgen/STAGE2_FALSIFICATION.json')
    ap.add_argument('--out-cells-csv', default='artifacts/b3_h_nextgen/STAGE2_CELLS.csv')
    a = ap.parse_args()
    run(Path(a.csv), Path(a.metadata), Path(a.out_json), Path(a.out_cells_csv))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
