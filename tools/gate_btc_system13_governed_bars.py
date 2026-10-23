"""Validate supplied, sealed OHLCV evidence; never collect, train or read holdout.

This is an import boundary, not authority to admit a new market-data source.
Admission receipts and instrument bindings must be supplied by source review.
The frozen System13 protocol and observed memberships remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROTOCOL = Path(__file__).resolve().parent / 'gate_btc_factory/SYSTEM13_PANEL_PROTOCOL_V1.json'
PROTOCOL_SHA256 = 'a8f90a269efd64cd939c8707b23c2db31962cdabf6742b0e97bb016be92e4670'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    return result.astimezone(timezone.utc)


def read_bound(root, relative, expected):
    root = root.resolve()
    p = (root / relative).resolve()
    if not p.is_relative_to(root) or not p.is_file():
        raise ValueError('EVIDENCE_PATH_OUTSIDE_BUNDLE_OR_MISSING')
    raw = p.read_bytes()
    if sha(raw) != expected:
        raise ValueError('SOURCE_EVIDENCE_HASH_MISMATCH')
    return json.loads(raw)


def protocol():
    raw = PROTOCOL.read_bytes()
    if sha(raw) != PROTOCOL_SHA256:
        raise ValueError('FROZEN_PROTOCOL_CHANGED')
    return json.loads(raw)


def inspect(root, bundle, membership):
    c = protocol()
    if bundle.get('schema') != 'qrds.system13.governed_bar_import.v1':
        raise ValueError('OHLCV_IMPORT_SCHEMA_REQUIRED')
    if membership.get('protocol_sha256') != PROTOCOL_SHA256:
        raise ValueError('MEMBERSHIP_PROTOCOL_MISMATCH')
    admission = read_bound(root, bundle['admission_path'], bundle['admission_sha256'])
    if (admission.get('status') != 'QUALIFIED_FOR_SYSTEM13_OHLCV_IMPORT'
            or admission.get('historical_reconstruction_allowed') is not False
            or admission.get('volume_unit') != 'BASE_ASSET'
            or admission.get('market') != 'SPOT'
            or admission.get('quote_currency') != 'USD'):
        raise ValueError('SOURCE_ADMISSION_OR_UNITS_NOT_QUALIFIED')
    # USD is literal here: USDT may not be relabelled USD without a reviewed FX adapter.
    for key in ('identity_evidence', 'tradability_evidence', 'adjustment_evidence'):
        read_bound(root, admission[key]['path'], admission[key]['sha256'])
    bindings = admission['instrument_bindings']
    members = {}
    for m in membership['rows']:
        key = (m['coin_id'], m['observed_at_utc'])
        if key in members:
            raise ValueError('DUPLICATE_MEMBERSHIP_ID_AND_TIME')
        members[key] = m
    output, seen = [], set()
    for item in bundle['bars']:
        raw = read_bound(root, item['raw_path'], item['raw_sha256'])
        if raw.get('schema') != 'qrds.system13.native_daily_ohlcv.v1':
            raise ValueError('NATIVE_DAILY_BAR_REQUIRED_NOT_OBSERVED_QUOTE')
        coin = raw['coin_id']; instrument = raw['venue_instrument']
        if bindings.get(coin) != instrument or raw['source_id'] != admission['source_id']:
            raise ValueError('EXACT_IDENTITY_BINDING_REQUIRED')
        begin, end, captured = (utc(raw[k]) for k in ('open_at_utc', 'close_at_utc', 'captured_at_utc'))
        if begin.time().isoformat() != '00:00:00' or end != begin + timedelta(days=1):
            raise ValueError('EXACT_UTC_DAILY_INTERVAL_REQUIRED')
        if not end <= captured < end + timedelta(days=1):
            raise ValueError('UNFINISHED_OR_LATE_HISTORICAL_BAR')
        if utc(admission['qualified_at_utc']) > begin:
            raise ValueError('SOURCE_NOT_QUALIFIED_BEFORE_SESSION')
        candidates = [m for (cid, _), m in members.items()
                      if cid == coin and utc(m['observed_at_utc']) <= begin]
        if not candidates:
            raise ValueError('NO_MEMBERSHIP_OBSERVED_BEFORE_SESSION')
        member = max(candidates, key=lambda m: utc(m['observed_at_utc']))
        if member['eligible_by_observed_flags_and_quote'] is not True:
            raise ValueError('EXCLUDED_MEMBER_CANNOT_BECOME_ELIGIBLE')
        values = {k: float(raw[k]) for k in c['required_qlib_fields']}
        if any(not math.isfinite(v) for v in values.values()):
            raise ValueError('NONFINITE_OHLCV')
        o, h, l, close = (values[k] for k in ('open', 'high', 'low', 'close'))
        if min(o, h, l, close) <= 0 or l > min(o, close) or h < max(o, close) or l > h:
            raise ValueError('INVALID_OHLC_ORDER')
        if values['volume'] < 0 or values['factor'] <= 0:
            raise ValueError('INVALID_VOLUME_OR_FACTOR')
        if (raw.get('volume_unit') != 'BASE_ASSET' or raw.get('quote_currency') != 'USD'
                or raw.get('adjustment_policy') != admission['adjustment_policy']):
            raise ValueError('BAR_UNITS_OR_ADJUSTMENT_MISMATCH')
        key = (begin.date().isoformat(), coin)
        if key in seen:
            raise ValueError('DUPLICATE_BAR_IDENTITY_AND_SESSION')
        seen.add(key)
        output.append({'session': key[0], 'coin_id': coin, 'venue_instrument': instrument,
                       **values, 'available_at_utc': captured.isoformat(),
                       'membership_observed_at_utc': member['observed_at_utc'],
                       'raw_sha256': item['raw_sha256'], 'admission_sha256': bundle['admission_sha256']})
    sessions = []
    for session in sorted({r['session'] for r in output}):
        begin = utc(session + 'T00:00:00Z')
        latest = {}
        for member in members.values():
            when = utc(member['observed_at_utc'])
            if when <= begin and (member['coin_id'] not in latest
                    or when > utc(latest[member['coin_id']]['observed_at_utc'])):
                latest[member['coin_id']] = member
        eligible = {coin for coin, m in latest.items() if m['eligible_by_observed_flags_and_quote'] is True}
        covered = {r['coin_id'] for r in output if r['session'] == session}
        coverage = len(covered) / len(eligible) if eligible else 0
        sessions.append({'session': session, 'observed_eligible_members': len(eligible),
                         'available_bar_count': len(covered), 'coverage_fraction': coverage,
                         'missing_coin_ids': sorted(eligible - covered),
                         'coverage_gate_pass': len(covered) >= c['min_assets_per_session']
                            and coverage >= c['min_coverage_fraction']})
    return {'schema': 'qrds.system13.governed_bar_import_review.v1',
            'protocol_sha256': PROTOCOL_SHA256, 'validated_source_rows': len(output),
            'rows': sorted(output, key=lambda r: (r['session'], r['coin_id'])),
            'sessions': sessions,
            'source_review_authority': 'EXTERNAL_ADMISSION_RECEIPT_REQUIRED_NOT_GRANTED_BY_IMPORTER',
            'chronological_partitions_qualified': False, 'training_ready': False,
            'holdout_read_allowed': False, 'system13_complete': False,
            'new_scientific_credit': 0, 'safety': c['safety']}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--membership', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = inspect(args.bundle.parent, json.loads(args.bundle.read_text()),
                     json.loads(args.membership.read_text()))
    raw = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + '\n'
    if args.out.exists() and args.out.read_text() != raw:
        raise ValueError('IMMUTABLE_IMPORT_OUTPUT_CHANGED')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(raw)


if __name__ == '__main__':
    main()
