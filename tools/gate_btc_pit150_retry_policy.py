"""Exact-identity, prospective request scheduling; no prices or universe edits."""
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

POLICY_PATH = Path(__file__).with_suffix('.json')

def load_policy():
    raw = POLICY_PATH.read_bytes()
    policy = json.loads(raw)
    policy['sha256'] = hashlib.sha256(raw).hexdigest()
    return policy

def decision(symbol, coin_id, cutoff, policy=None):
    p = policy if policy is not None else load_policy()
    if symbol in ('BTC', 'ETH') or not cutoff:
        return None
    day = date.fromisoformat(cutoff)
    if day < date.fromisoformat(p['effective_cutoff']):
        return None
    matches = [c for c in p['cases'] if c['symbol'] == symbol and c['coin_id'] == coin_id]
    if len(matches) != 1:
        return None
    case = matches[0]
    if day < date.fromisoformat(case.get('effective_cutoff', p['effective_cutoff'])):
        return None
    first = case['retry_from']
    next_due = None
    if first is not None:
        start = date.fromisoformat(first)
        interval = case['retry_interval_days']
        if type(interval) is not int or interval < 1:
            raise ValueError('invalid retry interval')
        elapsed = (day - start).days
        if elapsed >= 0 and elapsed % interval == 0:
            return None  # Allow original sources and full existing QA on a due day.
        next_due = start if elapsed < 0 else day + timedelta(days=interval - elapsed % interval)
    return {
        'policy_id': p['policy_id'], 'policy_sha256': p['sha256'],
        'symbol': symbol, 'coin_id': coin_id, 'cutoff': cutoff,
        'disposition': case['disposition'], 'next_retry_cutoff': next_due.isoformat() if next_due else None,
        'status': 'OPERATIONALLY_DEFERRED', 'source_requests': 0,
        'requires_new_evidence': first is None,
        'coverage_repaired': False, 'denominator_changed': False,
    }

def annotate_followup(report):
    p = load_policy()
    if date.fromisoformat(report['data_as_of']) < date.fromisoformat(p['effective_cutoff']):
        return report
    for row in report['assets']:
        schedule = decision(row['symbol'], row['pit150_identity'], report['data_as_of'], p)
        if schedule:
            row['request_schedule'] = schedule
            row['operational_repair_required'] = False
            row['next_action'] = ('WAIT_UNTIL_' + schedule['next_retry_cutoff']
                                  if schedule['next_retry_cutoff'] else 'REOPEN_ONLY_WITH_NEW_EXACT_SOURCE_EVIDENCE')
    report['retry_policy_id'] = p['policy_id']
    report['retry_policy_sha256'] = p['sha256']
    report['deferred_case_count'] = sum('request_schedule' in r for r in report['assets'])
    report['coverage_gap_is_not_new_repair'] = True
    return report

