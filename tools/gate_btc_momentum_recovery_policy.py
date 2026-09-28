"""Bounded current-cutoff retry policy; never changes scientific state."""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone

ACTIVE = {'in_progress', 'queued', 'waiting', 'requested', 'pending'}
RECOVERABLE = {'WAIT_SOURCE_PUBLICATION', 'RED_TRUE_PROCESSING_FAILURE',
               'BLOCKED_SOURCE_RETRY_EXHAUSTED'}


def assess(state, runs, at):
    target = (at.date() - timedelta(days=1)).isoformat()
    today = at.date().isoformat()
    attempts = len({r['databaseId'] for r in runs if r['createdAt'].startswith(today)})
    overlap = any(r['status'] in ACTIVE for r in runs)
    eligible = (state.get('repair_scope') == 'ORCHESTRATION_AND_DATA_DELIVERY_ONLY'
                and state.get('status') in RECOVERABLE
                and state.get('requested_cutoff', state.get('data_as_of')) == target
                and state.get('methodology_failure') is not True)
    dispatch = eligible and not overlap and attempts < 6
    reason = ('NOT_CURRENT_MECHANICAL_RECOVERY' if not eligible else
              'SKIP_ACTIVE_RUN' if overlap else
              'ATTEMPT_BUDGET_EXHAUSTED' if attempts >= 6 else 'RETRY_CURRENT_CUTOFF')
    return {'dispatch': dispatch, 'target': target, 'attempts': attempts,
            'max_daily_runs': 6, 'reason': reason, 'source_status': state.get('status'),
            'research_only': True, 'shadow_only': True, 'orders': 0, 'real_capital': 0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--runs', required=True)
    args = ap.parse_args()
    with open(args.state, encoding='utf-8') as f:
        state = json.load(f)
    with open(args.runs, encoding='utf-8') as f:
        runs = json.load(f)
    result = assess(state, runs, datetime.now(timezone.utc))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            for key in ('dispatch', 'target', 'attempts', 'reason'):
                f.write(f'{key}={str(result[key]).lower() if isinstance(result[key], bool) else result[key]}\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
