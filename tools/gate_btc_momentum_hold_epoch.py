#!/usr/bin/env python3
"""Approved, independent gross shadow accounting; old economics are immutable."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.gate_btc_momentum_economic_shadow import STRATS, load_json, top10

APPROVAL = ROOT / 'migration/reporting/momentum_m1m2_hold_epoch_20260928.json'
CONTRACT = ROOT / 'migration/reporting/momentum_m1m2_economic_contract_v1.json'
SAFETY = dict(research_only=True, shadow_only=True, not_approved=True,
              engine_feed=False, orders=0, real_capital=0, promotion_allowed=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(obj):
    return (json.dumps(obj, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes(encoded(obj))
    os.replace(temporary, path)


def immutable(path, obj):
    immutable_bytes(path, encoded(obj))


def immutable_bytes(path, raw):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('IMMUTABLE_EPOCH_EVIDENCE_CHANGED:' + path.name)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_bytes(raw)
        os.replace(temporary, path)


def setup(root, config, contract):
    if config['epoch_id'] != 'hold_20260928':
        raise ValueError('UNAPPROVED_EPOCH_ID')
    if config['rebalance_every_closes'] != 7 or config['initial_nav'] != 1:
        raise ValueError('UNAPPROVED_ACCOUNTING_POLICY')
    if any(config[k] for k in ('inherit_pnl', 'inherit_counters', 'historical_backfill', 'retune')):
        raise ValueError('UNAPPROVED_HISTORY_MUTATION')
    if contract['rebalance']['between_rebalances'] != 'HOLD':
        raise ValueError('FROZEN_CONTRACT_CHANGED')
    for name, seal in config['legacy_seals'].items():
        if digest((root / name).read_bytes()) != seal:
            raise ValueError('LEGACY_SEAL_MISMATCH:' + name)
    epoch = root / 'epochs' / config['epoch_id']
    immutable(epoch / 'APPROVAL.json', config)
    immutable(epoch / 'CONTRACT.json', contract)
    immutable(root / 'INTERRUPTED_EPOCH.json', {
        **SAFETY, 'status': 'CLOSED_INTERRUPTED_DIAGNOSTIC_ONLY',
        'legacy_files_sha256': config['legacy_seals'],
        'original_files_remain_in_place': True, 'historical_rewrite_performed': False,
        'reason': 'MISSING_CLOSES_AND_DAILY_EQUAL_WEIGHT_CONTRADICTED_WEEKLY_HOLD',
        'successor_epoch': config['epoch_id'], 'pnl_transferred': 0, 'counters_transferred': 0})
    immutable(root / 'ACTIVE_EPOCH.json', {
        **SAFETY, 'epoch_id': config['epoch_id'], 'relative_path': 'epochs/' + config['epoch_id'],
        'approval_sha256': digest(encoded(config)), 'contract_sha256': digest(encoded(contract))})
    return epoch


def validate_ledger(ledger, config, contract):
    if ledger['approval_sha256'] != digest(encoded(config)) or ledger['contract_sha256'] != digest(encoded(contract)):
        raise ValueError('EPOCH_AUTHORITY_CHANGED')
    rows = ledger['rows']
    if not rows or rows[0]['event'] != 'ACTIVATION' or rows[0]['return_observations'] != 0:
        raise ValueError('INVALID_ACTIVATION')
    for i, row in enumerate(rows):
        if row['return_observations'] != i:
            raise ValueError('OBSERVATION_COUNT_MISMATCH')
        if i and date.fromisoformat(row['cutoff']) - date.fromisoformat(rows[i-1]['cutoff']) != timedelta(days=1):
            raise ValueError('NON_CONTIGUOUS_EPOCH_HISTORY')
    state = ledger['state']
    if state['last_cutoff'] != rows[-1]['cutoff'] or state['return_observations'] != len(rows)-1:
        raise ValueError('STATE_HISTORY_MISMATCH')
    if state['closes_since_rebalance'] != state['return_observations'] % 7:
        raise ValueError('REBALANCE_COUNTER_MISMATCH')
    if any(state[k] != rows[-1][k] for k in ('nav', 'btc_nav')):
        raise ValueError('LAST_ROW_NAV_MISMATCH')
    if state['quantities'] != rows[-1]['quantities_after_close'] or state['holdings'] != rows[-1]['holdings_after_close']:
        raise ValueError('LAST_ROW_HOLDINGS_MISMATCH')
    for name in STRATS:
        if set(state['quantities'][name]) != set(state['holdings'][name]) or len(state['holdings'][name]) != 10:
            raise ValueError('QUANTITY_IDENTITY_MISMATCH')
        value = sum(q * state['last_prices'][a] for a, q in state['quantities'][name].items())
        if not math.isclose(value, state['nav'][name], rel_tol=1e-12):
            raise ValueError('QUANTITY_NAV_MISMATCH')


def advance(ledger, snapshot, prices, config, contract, evidence, at):
    """Pure transition. Revalue held quantities BEFORE any seven-close rebalance."""
    cutoff = snapshot['cutoff']
    if cutoff < config['first_eligible_cutoff']:
        raise ValueError('PRE_APPROVAL_CUTOFF')
    if cutoff != (at.date() - timedelta(days=1)).isoformat():
        raise ValueError('NOT_LATEST_COMPLETED_CLOSE_NO_BACKFILL')
    for p in prices.values():
        if not math.isfinite(p) or p <= 0:
            raise ValueError('INVALID_PRICE')
    current = {name: top10(snapshot, *fields) for name, fields in STRATS.items()}
    if ledger:
        validate_ledger(ledger, config, contract)
        state = copy.deepcopy(ledger['state'])
        delta = (date.fromisoformat(cutoff) - date.fromisoformat(state['last_cutoff'])).days
        if delta == 0:
            if ledger['rows'][-1]['evidence'] != evidence:
                raise ValueError('SAME_CUTOFF_EVIDENCE_CHANGED')
            return ledger, False
        if delta != 1:
            raise ValueError('GAP_OR_OUT_OF_ORDER_NO_SILENT_BRIDGE')
        previous_nav = dict(state['nav'])
        nav = {name: sum(q * prices[a] for a, q in state['quantities'][name].items()) for name in STRATS}
        count = state['return_observations'] + 1
        rebalance = count % 7 == 0
        daily = {name: nav[name] / previous_nav[name] - 1 for name in STRATS}
        btc_nav = state['btc_quantity'] * prices['BTC']
        btc_daily = btc_nav / state['btc_nav'] - 1
        event = 'REBALANCE' if rebalance else 'HOLD'
    else:
        state = {'activation_cutoff': cutoff, 'btc_quantity': 1 / prices['BTC']}
        nav = {name: 1.0 for name in STRATS}
        count, rebalance, event = 0, True, 'ACTIVATION'
        daily, btc_daily, btc_nav = {name: None for name in STRATS}, None, 1.0
        ledger = {**SAFETY, 'schema': 'gate_btc.momentum_hold_ledger.v1',
                  'epoch_id': config['epoch_id'], 'approval_sha256': digest(encoded(config)),
                  'contract_sha256': digest(encoded(contract)), 'rows': []}
    if rebalance:
        state['holdings'] = current
        state['quantities'] = {name: {a: nav[name] / 10 / prices[a] for a in current[name]} for name in STRATS}
    state.update(nav=nav, btc_nav=btc_nav, last_prices=prices, last_cutoff=cutoff,
                 return_observations=count, closes_since_rebalance=count % 7)
    row = {'cutoff': cutoff, 'observed_at_utc': at.isoformat(), 'event': event,
           'return_observations': count, 'nav': nav, 'daily_return_gross': daily,
           'btc_nav': btc_nav, 'btc_daily_return_gross': btc_daily,
           'total_return_gross': {name: nav[name]-1 for name in STRATS},
           'excess_vs_btc_percentage_points': {name: 100*(nav[name]-btc_nav) for name in STRATS},
           'illustrative_brl_value': {name: contract['reporting_base_brl']*nav[name] for name in STRATS},
           'illustrative_brl_pnl': {name: contract['reporting_base_brl']*(nav[name]-1) for name in STRATS},
           'reporting_currency_note': 'FIXED_NOTIONAL_ILLUSTRATION_NOT_REALIZED_BRL_OR_FX_ADJUSTED',
           'cost_status': 'N_D', 'net_return': None, 'evidence': evidence,
           'holdings_after_close': state['holdings'], 'quantities_after_close': state['quantities']}
    result = {**ledger, 'state': state, 'rows': ledger['rows'] + [row]}
    validate_ledger(result, config, contract)
    return result, True


def report(epoch, config, status, ledger=None, **extra):
    state = (ledger or {}).get('state', {})
    payload = {**SAFETY, 'schema': 'gate_btc.momentum_hold_status.v1', 'status': status,
        'epoch_id': config['epoch_id'], 'updated_at_utc': datetime.now(timezone.utc).isoformat(),
        'first_eligible_cutoff': config['first_eligible_cutoff'],
        'data_as_of': state.get('last_cutoff'), 'return_observations': state.get('return_observations', 0),
        'activation_cutoff': state.get('activation_cutoff'), 'nav': state.get('nav'),
        'btc_nav': state.get('btc_nav'), 'closes_since_rebalance': state.get('closes_since_rebalance', 0),
        'cost_status': 'N_D', 'net_return': None, 'backfill_performed': False,
        'economic_rows_appended': 0, 'terminal_observation_target': None,
        'weighting_audit': {'status': 'APPROVED_HOLD_ACCOUNTING', 'engine_changed': True,
                            'historical_rewrite_performed': False},
        'next_action': 'AUTOMATIC_DAILY_PROSPECTIVE_COLLECTION', **extra}
    if ledger:
        payload['latest_economics'] = ledger['rows'][-1]
    save(epoch / 'ECONOMICS_STATUS.json', payload)
    save(epoch / 'DELIVERY_STATUS.json', payload)
    return payload


def verify_sources(epoch, cutoff, evidence=None):
    path = epoch / 'source_prices' / cutoff / 'MANIFEST.json'
    manifest = load_json(path)
    if evidence and digest(path.read_bytes()) != evidence['price_manifest_sha256']:
        raise ValueError('SEALED_PRICE_MANIFEST_CHANGED')
    for name, key in [('required_prices.zip', 'prices_zip_sha256'), ('RAW_SOURCES.json.gz', 'raw_archive_sha256')]:
        if digest((path.parent / name).read_bytes()) != manifest[key]:
            raise ValueError('SOURCE_ARCHIVE_CORRUPT')
    return manifest, digest(path.read_bytes())


def run(args, clock=lambda: datetime.now(timezone.utc)):
    from tools.gate_btc_momentum_required_prices import collect
    config, contract = load_json(APPROVAL), load_json(CONTRACT)
    root = Path(args.ledger_dir)
    epoch = setup(root, config, contract)
    lp = epoch / 'LEDGER.json'
    ledger = load_json(lp) if lp.exists() else None
    if ledger:
        validate_ledger(ledger, config, contract)
    at = clock()
    if at < datetime.fromisoformat(config['approved_at_utc']):
        raise ValueError('APPROVAL_NOT_EFFECTIVE')
    latest = (at.date() - timedelta(days=1)).isoformat()
    if latest < config['first_eligible_cutoff']:
        if ledger:
            raise ValueError('CLOCK_BEFORE_EXISTING_EPOCH')
        return report(epoch, config, 'WAITING_FIRST_POST_APPROVAL_CLOSE')
    snapshot_bytes = Path(args.snapshot).read_bytes()
    snapshot = json.loads(snapshot_bytes)
    if snapshot['cutoff'] != latest:
        raise ValueError('CURRENT_MOMENTUM_SIGNAL_MISSING_NO_BACKFILL')
    if ledger and snapshot['cutoff'] == ledger['state']['last_cutoff']:
        evidence = ledger['rows'][-1]['evidence']
        if evidence['snapshot_sha256'] != digest(snapshot_bytes):
            raise ValueError('SAME_CUTOFF_SIGNAL_CHANGED')
        verify_sources(epoch, latest, evidence)
        if digest((epoch / 'signals' / (latest + '.json')).read_bytes()) != evidence['snapshot_sha256']:
            raise ValueError('SEALED_SIGNAL_CHANGED')
        return report(epoch, config, 'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY', ledger, idempotent=True)
    if ledger and (date.fromisoformat(latest) - date.fromisoformat(ledger['state']['last_cutoff'])).days != 1:
        raise ValueError('GAP_OR_OUT_OF_ORDER_NO_SILENT_BRIDGE')
    if args.phase == 'prepare':
        manifest = collect(snapshot, ledger['state'] if ledger else None,
                           epoch / 'source_prices', Path(args.output_zip), clock=clock)
        save(epoch / 'PRICE_COVERAGE_STATUS.json', {**SAFETY, 'status': 'PASS_REQUIRED_PRICE_COVERAGE',
            'cutoff': latest, 'required_assets': manifest['required_assets'],
            'available_at_utc': manifest['available_at_utc'], 'scientific_credit': 0})
        return {'status': 'PRICES_READY', 'price_count': manifest['price_count']}
    manifest, manifest_sha = verify_sources(epoch, latest)
    if manifest['cutoff'] != latest or datetime.fromisoformat(manifest['available_at_utc']).date() != at.date():
        raise ValueError('PRICE_EVIDENCE_NOT_CURRENT')
    prices = {r['symbol']: r['close_usd'] for r in manifest['prices']}
    evidence = {'snapshot_sha256': digest(snapshot_bytes), 'price_manifest_sha256': manifest_sha,
                'source_available_at_utc': manifest['available_at_utc']}
    result, changed = advance(ledger, snapshot, prices, config, contract, evidence, at)
    immutable_bytes(epoch / 'signals' / (latest + '.json'), snapshot_bytes)
    # One atomic authority file contains BOTH history and state. Reports are rebuildable.
    save(lp, result)
    return report(epoch, config, 'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY', result,
                  economic_rows_appended=int(changed))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--ledger-dir', required=True)
    ap.add_argument('--output-zip', required=True)
    ap.add_argument('--phase', choices=['prepare', 'append'], required=True)
    args = ap.parse_args()
    try:
        result = run(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        config = load_json(APPROVAL)
        epoch = Path(args.ledger_dir) / 'epochs' / config['epoch_id']
        lp = epoch / 'LEDGER.json'
        ledger = load_json(lp) if lp.exists() else None
        result = report(epoch, config, 'FAILED_ECONOMIC_DELIVERY', ledger,
            error=str(exc), next_action='REPAIR_FAILURE_NO_RESET_NO_BACKFILL',
            source_failures=getattr(exc, 'failures', {}), failure_evidence=getattr(exc, 'evidence_path', None))
        print(json.dumps(result, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
