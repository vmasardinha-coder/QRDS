#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import date as dt_date
from pathlib import Path
from statistics import median

import pandas as pd
import requests

from gate_btc_b3_h1_daily import fetch_raw, load_schedule, structural_qa
from gate_btc_b3_h1_parser import process_zip

CONTRACT_PATH = Path('tools/gate_btc_b3_h31_source_binding_contract_v1.json')
FREEZE_PATH = Path('tools/gate_btc_b3_h31_prospective_freeze.json')
EXPECTED_SAFETY = {
    'orders': 0,
    'real_capital': 0,
    'engine_feed': False,
    'not_approved': True,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return sha256_bytes(raw)


def load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise RuntimeError(f'EXPECTED_OBJECT {path}')
    return obj


def validate_contract() -> tuple[dict, dict]:
    c = load_json(CONTRACT_PATH)
    f = load_json(FREEZE_PATH)
    if c.get('schema') != 'gate_btc.b3.h31.source_binding.v1':
        raise RuntimeError('CONTRACT_SCHEMA_MISMATCH')
    if c.get('approval_status') != 'APPROVED_FOR_SEPARATE_PROSPECTIVE':
        raise RuntimeError('H31_NOT_APPROVED_FOR_SEPARATE_PROSPECTIVE')
    if c.get('freeze_rule_hash_sha256') != f.get('rule_hash_sha256'):
        raise RuntimeError('FREEZE_HASH_MISMATCH')
    if c.get('backfill_forbidden') is not True or c.get('late_reconstruction_forbidden') is not True:
        raise RuntimeError('BACKFILL_BOUNDARY_MISSING')
    if c.get('retune_forbidden') is not True or c.get('partial_prospective_feedback_forbidden') is not True:
        raise RuntimeError('RETUNE_OR_FEEDBACK_BOUNDARY_MISSING')
    if c.get('h1_economics_read') is not False:
        raise RuntimeError('H1_ECONOMICS_BOUNDARY_BROKEN')
    for k, v in EXPECTED_SAFETY.items():
        if c.get(k) != v or f.get(k) != v:
            raise RuntimeError(f'SAFETY_MISMATCH {k}')
    rule = c.get('rule', {})
    required = {
        'signal_asset': 'WDO',
        'observation_minutes': 30,
        'standardizer': 'trailing_20_session_median_absolute_30m_move_bps',
        'trigger_abs_z_gte': 1.5,
        'traded_asset': 'WIN',
        'direction': 'opposite_signal',
        'execution': 'next_bar_open',
        'hold_minutes': 120,
        'reference_roundtrip_cost_bp': 2.0,
        'stress_roundtrip_cost_bp': 3.0,
    }
    for k, v in required.items():
        if rule.get(k) != v:
            raise RuntimeError(f'RULE_MISMATCH {k}')
    return c, f


def brnum(s: pd.Series) -> pd.Series:
    return pd.to_numeric(
        s.astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='coerce',
    )


def load_frozen_historical_wdo(contract: dict) -> list[dict]:
    src = contract['historical_warmup']
    url = (
        f"https://raw.githubusercontent.com/{src['source_repo']}/{src['source_commit']}/"
        f"{src['file']}"
    )
    r = requests.get(url, timeout=180)
    r.raise_for_status()
    x = pd.read_csv(io.StringIO(r.text), sep=';', dtype=str)
    cols = {z.lower().strip(): z for z in x.columns}
    ts = pd.to_datetime(
        x[cols['data']].str.strip() + ' ' + x[cols['hora']].str.strip(),
        dayfirst=True,
        errors='raise',
    ).dt.tz_localize(contract['target_timezone'])
    d = pd.DataFrame({
        'timestamp': ts,
        'open': brnum(x[cols['abertura']]),
        'close': brnum(x[cols['fechamento']]),
    }).dropna().sort_values('timestamp').drop_duplicates('timestamp')
    cutoff = pd.Timestamp(src['cutoff_exclusive'], tz=contract['target_timezone'])
    d = d[d['timestamp'] < cutoff]
    d['session'] = d['timestamp'].dt.date.astype(str)
    rows: list[dict] = []
    for session, g in d.groupby('session'):
        g = g.sort_values('timestamp').reset_index(drop=True)
        if len(g) < 6:
            continue
        first = g.iloc[:6]
        dt = first['timestamp'].diff().dropna().dt.total_seconds()
        if (first.iloc[0]['timestamp'].hour, first.iloc[0]['timestamp'].minute) != (9, 0):
            continue
        if not dt.empty and (dt != 300).any():
            continue
        o = float(first.iloc[0]['open'])
        c30 = float(first.iloc[-1]['close'])
        if o <= 0 or c30 <= 0:
            continue
        rows.append({'date': str(session), 'ret30_bps': (c30 / o - 1.0) * 10000.0, 'source': 'FROZEN_COMMUNITY_WARMUP'})
    if len(rows) < 20:
        raise RuntimeError(f'INSUFFICIENT_FROZEN_WARMUP rows={len(rows)}')
    return rows


def session_ret30(m5: pd.DataFrame, root: str) -> float:
    g = m5[m5['root'] == root].copy().sort_values('timestamp').reset_index(drop=True)
    if len(g) < 6:
        raise RuntimeError(f'{root}_MISSING_FIRST_30M')
    o = float(g.iloc[0]['open'])
    c30 = float(g.iloc[5]['close'])
    if o <= 0 or c30 <= 0:
        raise RuntimeError(f'{root}_BAD_FIRST_30M_PRICES')
    return (c30 / o - 1.0) * 10000.0


def fetch_official_session(session_date: str, schedule: dict[str, dict[str, str]]) -> tuple[pd.DataFrame, dict]:
    if session_date not in schedule:
        raise RuntimeError(f'NO_FROZEN_FRONT_SCHEDULE_FOR_DATE {session_date}')
    raw, source = fetch_raw(session_date)
    if raw is None:
        raise RuntimeError(f"SOURCE_NOT_READY {session_date} {source.get('state')}")
    front = schedule[session_date]
    m1, m5, stats, member = process_zip(raw, session_date, front)
    qa = structural_qa(session_date, front, m1, m5)
    evidence = {
        'date': session_date,
        'source_sha256': source['sha256'],
        'source_url': source['url'],
        'source_member': member,
        'front_contracts': front,
        'qa': qa,
        'engine_stats': stats,
    }
    return m5, evidence


def load_or_build_official_warmup(
    ledger_dir: Path,
    schedule: dict[str, dict[str, str]],
    target_date: str,
) -> list[dict]:
    warm_dir = ledger_dir / 'warmup'
    warm_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for d in sorted(k for k in schedule if '2026-08-10' <= k < target_date):
        p = warm_dir / f'{d}.json'
        if p.exists():
            rec = load_json(p)
        else:
            m5, ev = fetch_official_session(d, schedule)
            rec = {
                'schema': 'gate_btc.b3.h31.warmup_session.v1',
                'date': d,
                'ret30_bps': session_ret30(m5, 'WDO'),
                'source_sha256': ev['source_sha256'],
                'front_contracts': ev['front_contracts'],
                'structural_qa': 'PASS',
                'prospective_scored': False,
                'h1_economics_read': False,
            }
            p.write_text(json.dumps(rec, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        rows.append({'date': d, 'ret30_bps': float(rec['ret30_bps']), 'source': 'OFFICIAL_B3_WARMUP'})
    return rows


def compute_event(target_date: str, contract: dict, ledger_dir: Path) -> tuple[dict, dict]:
    first_eligible = dt_date.fromisoformat(contract['first_eligible_date'])
    target = dt_date.fromisoformat(target_date)
    if target < first_eligible:
        raise RuntimeError(f'BACKFILL_FORBIDDEN target={target_date} first_eligible={first_eligible.isoformat()}')

    schedule = load_schedule()
    hist = load_frozen_historical_wdo(contract)
    official_warm = load_or_build_official_warmup(ledger_dir, schedule, target_date)
    prior = sorted(hist + official_warm, key=lambda x: x['date'])
    prior = [r for r in prior if r['date'] < target_date]
    if len(prior) < 20:
        raise RuntimeError(f'INSUFFICIENT_TRAILING_20 rows={len(prior)}')
    trailing = prior[-20:]
    scale = float(median(abs(float(r['ret30_bps'])) for r in trailing))
    if scale <= 0:
        raise RuntimeError('NONPOSITIVE_TRAILING_SCALE')

    m5, evidence = fetch_official_session(target_date, schedule)
    wdo_ret30 = session_ret30(m5, 'WDO')
    z = wdo_ret30 / scale
    trigger = abs(z) >= float(contract['rule']['trigger_abs_z_gte'])

    win = m5[m5['root'] == 'WIN'].copy().sort_values('timestamp').reset_index(drop=True)
    if len(win) <= 30:
        raise RuntimeError('WIN_NOT_ENOUGH_BARS_FOR_120M_HOLD')
    side = 0
    gross_bps = None
    if trigger:
        side = -1 if wdo_ret30 > 0 else 1
        entry = float(win.iloc[6]['open'])
        exit_ = float(win.iloc[30]['open'])
        gross_bps = side * (exit_ / entry - 1.0) * 10000.0

    status_path = ledger_dir / 'STATUS.json'
    previous_hash = None
    previous_count = 0
    previous_latest = None
    if status_path.exists():
        old = load_json(status_path)
        previous_hash = old.get('last_event_hash')
        previous_count = int(old.get('eligible_observations', 0))
        previous_latest = old.get('latest_date')
        if previous_latest and target_date <= previous_latest:
            raise RuntimeError(f'BACKFILL_OR_REWRITE_FORBIDDEN target={target_date} latest={previous_latest}')

    event = {
        'schema': 'gate_btc.b3.h31.prospective_event.v1',
        'date': target_date,
        'freeze_rule_hash_sha256': contract['freeze_rule_hash_sha256'],
        'previous_event_hash': previous_hash,
        'source': evidence,
        'warmup': {
            'trailing_session_dates': [r['date'] for r in trailing],
            'trailing_20_median_abs_30m_bps': scale,
            'uses_scored_prospective_rows_for_warmup': False,
        },
        'signal': {
            'wdo_ret30_bps': wdo_ret30,
            'standardized_impulse': z,
            'trigger': trigger,
            'side': side,
        },
        'sealed_economics': {
            'exposed_to_factory_or_discovery': False,
            'gross_bps': gross_bps,
            'reference_net_bps': None if gross_bps is None else gross_bps - 2.0,
            'stress_net_bps': None if gross_bps is None else gross_bps - 3.0,
        },
        'h1_economics_read': False,
        'partial_prospective_feedback_allowed': False,
        'orders': 0,
        'real_capital': 0,
        'engine_feed': False,
        'not_approved': True,
    }
    event['event_hash_sha256'] = sha256_json(event)

    status = {
        'schema': 'gate_btc.b3.h31.prospective_status.v2',
        'status': 'ACTIVE_PROSPECTIVE',
        'clock_started': True,
        'eligible_observations': previous_count + 1,
        'latest_date': target_date,
        'last_event_hash': event['event_hash_sha256'],
        'freeze_rule_hash_sha256': contract['freeze_rule_hash_sha256'],
        'partial_prospective_economics_exposed': False,
        'h1_economics_read': False,
        'orders': 0,
        'real_capital': 0,
        'engine_feed': False,
        'not_approved': True,
    }
    return event, status


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--date')
    ap.add_argument('--ledger-dir', default='runtime/ledgers/b3_h31_prospective')
    ap.add_argument('--validate-contract-only', action='store_true')
    args = ap.parse_args()

    contract, _ = validate_contract()
    if args.validate_contract_only:
        print(json.dumps({'status': 'PASS_CONTRACT', 'approval_status': contract['approval_status']}, sort_keys=True))
        return 0
    if not args.date:
        raise SystemExit('FAIL --date is required unless --validate-contract-only')

    ledger_dir = Path(args.ledger_dir)
    ledger_dir.mkdir(parents=True, exist_ok=True)
    event_path = ledger_dir / 'events' / f'{args.date}.json'
    event_path.parent.mkdir(parents=True, exist_ok=True)
    if event_path.exists():
        existing = load_json(event_path)
        print(json.dumps({'status': 'IDEMPOTENT_ALREADY_PRESENT', 'date': args.date, 'event_hash': existing.get('event_hash_sha256')}, sort_keys=True))
        return 0

    event, status = compute_event(args.date, contract, ledger_dir)
    event_path.write_text(json.dumps(event, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    (ledger_dir / 'STATUS.json').write_text(json.dumps(status, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': status['status'],
        'date': args.date,
        'eligible_observations': status['eligible_observations'],
        'clock_started': status['clock_started'],
        'partial_prospective_economics_exposed': False,
        'h1_economics_read': False,
    }, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
