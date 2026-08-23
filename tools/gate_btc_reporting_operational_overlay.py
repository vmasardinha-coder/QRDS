#!/usr/bin/env python3
"""Add V16B and Momentum delivery status to the reporting-only current-state JSON.

Reporting only: no methodology, portfolio, order or capital mutation.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.is_file() else None


def iso(value):
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def freshness(obj, reference):
    if obj is None:
        return 'MISSING'
    d=iso(obj.get('data_as_of'))
    if d is None:
        return 'UNKNOWN_DATE'
    return 'FRESH' if reference is None or d >= reference else 'STALE'


def safe(name, obj):
    if obj is None:
        return
    for key, expected in {
        'research_only': True,
        'not_approved': True,
        'orders_generated': 0,
        'real_capital_used': 0,
    }.items():
        if key in obj and obj[key] != expected:
            raise SystemExit(f'unsafe {name}: {key}={obj[key]!r}')
    if obj.get('engine_feed') is True or obj.get('promotion_allowed') is True:
        raise SystemExit(f'unsafe {name}: operational boundary violated')


def enrich(runtime_root: Path, current: dict) -> dict:
    reference=iso(current.get('reference_data_date'))
    v16p=runtime_root/'ledgers/v16b/STATUS.json'
    momp=runtime_root/'ledgers/momentum_m1_m2/STATUS.json'
    v16=load(v16p); mom=load(momp)
    safe('v16b',v16); safe('momentum_m1_m2',mom)

    current.setdefault('components',{})['v16b']={
        'status':(v16 or {}).get('status','MISSING'),
        'freshness':freshness(v16,reference),
        'canonical_cycle_count':(v16 or {}).get('canonical_cycle_count'),
        'v16b_preflight':(v16 or {}).get('v16b_preflight'),
        'v16b_rehearsal':(v16 or {}).get('v16b_rehearsal'),
        'signal_producer':(v16 or {}).get('signal_producer'),
        'signal_seal':(v16 or {}).get('signal_seal'),
        'entry_seal':(v16 or {}).get('entry_seal'),
        'next_canonical_event':(v16 or {}).get('next_canonical_event'),
        'source':'ledgers/v16b/STATUS.json',
    }
    current['components']['momentum_m1_m2']={
        'status':(mom or {}).get('status','MISSING'),
        'freshness':freshness(mom,reference),
        'observed_snapshots':(mom or {}).get('observed_snapshots'),
        'last_run_state':(mom or {}).get('last_run_state'),
        'methodology_failure':(mom or {}).get('methodology_failure'),
        'm1_summary':(mom or {}).get('m1_summary'),
        'm2_summary':(mom or {}).get('m2_summary'),
        'source':'ledgers/momentum_m1_m2/STATUS.json',
    }

    warnings=current.setdefault('warnings',{})
    stale=list(warnings.get('stale_components',[]))
    missing=list(warnings.get('missing_or_undated_components',[]))
    for name in ('v16b','momentum_m1_m2'):
        f=current['components'][name]['freshness']
        if str(f).startswith('STALE') and name not in stale:
            stale.append(name)
        if f in {'MISSING','UNKNOWN_DATE'} and name not in missing:
            missing.append(name)
    warnings['stale_components']=stale
    warnings['missing_or_undated_components']=missing
    current['delivery_complete']=not stale and not missing
    current['status']='PASS' if current['delivery_complete'] else 'BLOCKED_INCOMPLETE_DELIVERY'
    current.setdefault('sources',{})['v16b']={'exists':v16p.is_file(),'path':str(v16p)}
    current['sources']['momentum_m1_m2']={'exists':momp.is_file(),'path':str(momp)}
    return current


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--runtime-root',type=Path,required=True)
    p.add_argument('--state',type=Path,required=True)
    a=p.parse_args()
    state=load(a.state)
    if not state:
        raise SystemExit('base reporting state missing')
    state=enrich(a.runtime_root,state)
    a.state.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({
        'status':state['status'],
        'v16b':state['components']['v16b'],
        'momentum_m1_m2':state['components']['momentum_m1_m2'],
        'orders_generated':0,'real_capital_used':0,
    },indent=2,sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
