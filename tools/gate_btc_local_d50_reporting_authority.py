"""Read-only local D50 authority; downloaded reports never select its counter."""
import csv
import hashlib
import json
from pathlib import Path

STRATEGIES = ('D50_CONTROL', 'D50_COST_AWARE', 'D50_EXIT_2SIGMA')


def load_local_d50(root: Path) -> dict:
    state = root / 'state' / 'D50_PROSPECTIVE_STATUS_V2.json'
    ledger = root / 'state' / 'd50_prospective_observations_v2.csv'
    result = {'status': 'LOCAL_D50_AUTHORITY_BLOCKED', 'observations': None,
              'next_checkpoint': None, 'source_data_date': None, 'summaries': {},
              'source_file': str(state), 'source_hashes': {}, 'reporting_only': True,
              'scientific_authority': False, 'orders': 0, 'real_capital': 0}
    try:
        raw, rows_raw = state.read_bytes(), ledger.read_bytes()
        obj = json.loads(raw.decode('utf-8-sig'))
        result['source_hashes'] = {'status_sha256': hashlib.sha256(raw).hexdigest(),
                                   'ledger_sha256': hashlib.sha256(rows_raw).hexdigest()}
        n = obj.get('paired_prospective_observations')
        if type(n) is not int or n < 1:
            raise ValueError('INVALID_COUNTER')
        if (obj.get('research_only') is not True or obj.get('orders') != 0
                or obj.get('capital') != 0 or obj.get('operational_status') != 'NOT_APPROVED'
                or obj.get('historical_backfill_counted_as_prospective') is not False
                or obj.get('d50_ingestion_gate') != 'PASS'):
            raise ValueError('BOUNDARY_OR_GATE_MISMATCH')
        all_rows = list(csv.DictReader(rows_raw.decode('utf-8-sig').splitlines()))
        date_sets = []
        for strategy in STRATEGIES:
            rows = [r for r in all_rows if r.get('strategy') == strategy
                    and r.get('record_type') == 'PROSPECTIVE_OBSERVATION']
            dates = {r['date'] for r in rows}
            if len(rows) != n or len(dates) != n:
                raise ValueError('LEDGER_COUNTER_OR_DUPLICATE_MISMATCH')
            if sorted(int(r['observation_number']) for r in rows) != list(range(1, n + 1)):
                raise ValueError('OBSERVATION_SEQUENCE_MISMATCH')
            if any(r['gate_anchor_utc'] != obj.get('gate_anchor_utc')
                   or r.get('status') != 'ADMITTED_BY_FROZEN_GATE'
                   or float(r.get('orders', 'nan')) != 0
                   or float(r.get('capital', 'nan')) != 0 for r in rows):
                raise ValueError('LEDGER_BOUNDARY_MISMATCH')
            summary = obj.get('summaries', {}).get(strategy, {})
            if (summary.get('observations') != n or summary.get('end') != max(dates)
                    or obj.get('latest_prospective_date') != max(dates)
                    or obj.get('first_prospective_date') != min(dates)):
                raise ValueError('SUMMARY_DATE_OR_COUNTER_MISMATCH')
            date_sets.append(dates)
        if any(dates != date_sets[0] for dates in date_sets[1:]):
            raise ValueError('PAIRED_DATE_MISMATCH')
        result.update(status='LOCAL_D50_AUTHORITY_PASS', observations=n,
                      next_checkpoint=obj.get('next_checkpoint'),
                      source_data_date=obj['latest_prospective_date'],
                      summaries={s: obj['summaries'][s] for s in STRATEGIES})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result['reason'] = type(exc).__name__ + ':' + str(exc)
    return result
