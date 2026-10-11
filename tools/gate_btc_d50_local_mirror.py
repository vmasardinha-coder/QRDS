#!/usr/bin/env python3
"""Prepare reporting mirrors from verified existing local D50 evidence.

Reads the complete immutable economic ledger and qualification hash chain. Writes
only reporting summaries in an output directory. Never collects, replays, admits
data, changes scientific decisions, or writes to its local evidence inputs.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from .gate_btc_d50_mirror_reconcile import (build_audit, load_json, parse_datetime, ReconciliationError)
    from .gate_btc_d50_runtime_authority import canonical_sha, require_safe
except ImportError:
    from gate_btc_d50_mirror_reconcile import (build_audit, load_json, parse_datetime, ReconciliationError)
    from gate_btc_d50_runtime_authority import canonical_sha, require_safe


def require(condition, message):
    if not condition:
        raise ReconciliationError(message)


def verify_qualification(root: Path, latest_date: str) -> dict:
    cert = load_json(root / 'qualification_status.json')
    require(cert.get('schema') == 'gate_btc.qualification_certificate.v1', 'qualification schema mismatch')
    require(cert.get('WINDOW_MAY_START') is False and cert.get('CAPITAL_REAL_ALLOWED') is False, 'qualification authority changed')
    paths = sorted((root / 'snapshots').glob('*/snapshot.json'))
    require(len(paths) == cert.get('snapshot_count_total') and bool(paths), 'qualification snapshot inventory mismatch')
    previous = None
    streak = 0
    snapshots = []
    for path in paths:
        s = load_json(path)
        require(s.get('schema') == 'gate_btc.prospective_snapshot.v1', 'snapshot schema mismatch')
        require(s.get('snapshot_id') == path.parent.name, 'snapshot date/path mismatch')
        require(s.get('candidate') == cert.get('candidate'), 'snapshot candidate mismatch')
        require(s.get('WINDOW_MAY_START') is False and s.get('CAPITAL_REAL_ALLOWED') is False, 'snapshot authority changed')
        clean = dict(s)
        tip = clean.pop('snapshot_sha256', None)
        digest = hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        require(tip == digest and s.get('previous_snapshot_sha256') == previous, 'qualification hash chain mismatch')
        previous = tip
        if s.get('qualification_pass') is True:
            obs = s.get('observations') or []
            require(s.get('synchronized_failure') is False and s.get('coverage_pct') == 1, 'qualified snapshot coverage mismatch')
            require(len(obs) == s.get('universe_size') == s.get('fresh_count') > 0, 'qualified snapshot universe mismatch')
            require(len({x.get('symbol') for x in obs}) == len(obs), 'duplicate qualified symbols')
            for x in obs:
                require(x.get('date') == s['snapshot_id'] and all(x.get(k) is True for k in ('eligible','fresh','present')), 'qualified observation mismatch')
                available = parse_datetime(x.get('available_at_utc'), 'available_at_utc')
                cutoff = parse_datetime(s.get('decision_cutoff_utc'), 'decision_cutoff_utc')
                require(available <= cutoff and x.get('decision_cutoff_utc') == s.get('decision_cutoff_utc'), 'qualified observation arrived after cutoff')
            streak += 1
        else:
            streak = 0
        snapshots.append(s)
    require(snapshots[-1]['snapshot_id'] == latest_date, 'economic/qualification dates differ')
    require(cert.get('hash_chain_valid') is True and streak == cert.get('latest_consecutive_pass_count'), 'qualification streak mismatch')
    required = cert.get('required_consecutive_pass_count')
    require(isinstance(required, int) and required > 0, 'qualification target invalid')
    require(cert.get('qualified') == (streak >= required), 'qualification certificate state mismatch')
    selected = snapshots[-required:] if streak >= required else []
    require(cert.get('qualified_snapshot_ids') == [s['snapshot_id'] for s in selected], 'certificate snapshot IDs mismatch')
    require(cert.get('qualified_snapshot_hashes') == [s['snapshot_sha256'] for s in selected], 'certificate snapshot hashes mismatch')
    tip = snapshots[-1]
    return {'current': streak, 'target': required, 'status': f'ACTIVE_CONSECUTIVE_PASS_CHAIN_{streak}_OF_{required}',
            'snapshot_count_total': len(paths), 'latest_snapshot_id': latest_date, 'latest_snapshot_sha256': previous,
            'hash_chain_valid': True, 'qualified': cert['qualified'], 'fresh_count': tip['fresh_count'],
            'coverage_pct': tip['coverage_pct'], 'universe_size': tip['universe_size'], 'synchronized_failure': tip['synchronized_failure'],
            'latest_snapshot_qualification_pass': tip['qualification_pass'], 'source': 'VERIFIED_LOCAL_QUALIFICATION_HASH_CHAIN',
            'certificate_sha256': hashlib.sha256((root/'qualification_status.json').read_bytes()).hexdigest(),
            'user_action_required': False, 'duplicate_reports_double_counted': False, 'retroactive_fill_used': False,
            'WINDOW_MAY_START': False, 'CAPITAL_REAL_ALLOWED': False}


def prepare(local_root: Path, qualification_root: Path, runtime_root: Path, today: date | None = None):
    today = today or datetime.now(timezone.utc).date()
    state = local_root/'state'
    status_path = state/'D50_PROSPECTIVE_STATUS_V2.json'
    local = load_json(status_path)
    latest = local.get('latest_prospective_date')
    require(latest == (today-timedelta(days=1)).isoformat(), 'local D50 evidence is stale or future')
    remote_path = runtime_root/'ledgers/d50/STATUS.json'
    audit = build_audit(local_status_path=status_path, local_ledger_path=state/'d50_prospective_observations_v2.csv', remote_status_path=remote_path)
    qualification = verify_qualification(qualification_root, latest)
    remote = load_json(remote_path)
    require(qualification['snapshot_count_total'] >= (remote.get('data_qualification') or {}).get('snapshot_count_total', 0), 'qualification count regression')
    target = local.get('next_checkpoint')
    require(isinstance(target, int) and not isinstance(target, bool) and target >= local['paired_prospective_observations'] > 0, 'local checkpoint invalid')
    hashes = local.get('source_hashes') or {}
    require(all(isinstance(hashes.get(k), str) and len(hashes[k]) == 64 for k in ('ohlc','funding')), 'local source hashes missing')
    # The full ledger audit proves existing observations; this mirror creates none.
    ledger = {'status': 'ACTIVE', 'current': local['paired_prospective_observations'], 'target': target,
              'next_checkpoint': target, 'checkpoint_due': local.get('checkpoint_due', False),
              'first_prospective_date': local['first_prospective_date'], 'latest_prospective_date': latest,
              'excluded_historical_backfill_dates': local.get('excluded_historical_backfill_dates', []),
              'historical_backfill_counts_as_prospective': False, 'frozen_history_must_be_preserved': True,
              'mutation_performed': False, 'mirror_alignment_only': True, 'user_action_required': False,
              'source': 'VERIFIED_LOCAL_IMMUTABLE_LEDGER_AND_QUALIFICATION_CHAIN', 'source_hashes': hashes,
              'local_status_sha256': audit['local_checkpoint']['status_sha256'], 'local_ledger_sha256': audit['local_checkpoint']['ledger_sha256']}
    audit['qualification'] = qualification
    audit['status'] = 'PASS_D50_LOCAL_EVIDENCE_ALIGNED'
    audit['alignment_sha256'] = canonical_sha(audit)
    safe = {'research_only': True, 'shadow_only': True, 'not_approved': True, 'promotion_allowed': False, 'orders_generated': 0, 'real_capital_used': 0}
    note = f"D50 reconciled through {latest}: economic ledger {ledger['current']}/{target}; qualification {qualification['current']}/{qualification['target']}. Existing local evidence verified; no economic rows imported or mutated; WINDOW_MAY_START remains false."
    mirror = {**safe, 'schema': remote['schema'], 'data_as_of': latest, 'prospective_immutable_ledger': ledger,
              'data_qualification': qualification, 'source_reconciliation_note': note,
              'mirror_alignment': {'status': audit['status'], 'alignment_sha256': audit['alignment_sha256'], 'economic_rows_imported': 0, 'economic_rows_mutated': 0, 'duplicate_reports_double_counted': False, 'authority': 'VERIFIED_LOCAL_EXISTING_EVIDENCE_ONLY'}}
    measurement = load_json(runtime_root/'GATE_BTC_MEASUREMENT_STATUS.json')
    require_safe(measurement, 'measurement')
    measurement = deepcopy(measurement)
    measurement.update(d50_prospective_immutable_ledger=ledger, d50_data_qualification=qualification, reconciliation_note=note,
                       d50_reconciliation={'status': audit['status'], 'alignment_sha256': audit['alignment_sha256'], 'economic_rows_imported_by_alignment': 0, 'economic_rows_mutated_by_alignment': 0, 'duplicate_reports_double_counted': False})
    measurement['status_sha256'] = canonical_sha(measurement)
    mirror['source_measurement_status_sha256'] = measurement['status_sha256']
    mirror['status_sha256'] = canonical_sha(mirror)
    return mirror, measurement, audit


def main():
    ap = argparse.ArgumentParser()
    for name in ('local-root','qualification-root','runtime-root','output-root'):
        ap.add_argument('--'+name, type=Path, required=True)
    a = ap.parse_args()
    mirror, measurement, audit = prepare(a.local_root, a.qualification_root, a.runtime_root)
    for relative, obj in [('ledgers/d50/STATUS.json',mirror), ('GATE_BTC_MEASUREMENT_STATUS.json',measurement), ('ledgers/d50/LOCAL_MIRROR_AUDIT.json',audit)]:
        p = a.output_root/relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps({'status':audit['status'], 'current':mirror['prospective_immutable_ledger']['current'], 'target':mirror['prospective_immutable_ledger']['target'], 'qualification':mirror['data_qualification']['current'], 'economic_rows_mutated':0, 'orders':0, 'capital':0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
