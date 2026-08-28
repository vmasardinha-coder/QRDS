#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tools/gate_btc_research_factory_status.json'
PLAN=ROOT/'tools/gate_btc_factory/FACTORY_TRANSITIONS_RUNTIME.json'
WATCH=ROOT/'tools/gate_btc_factory/WATCHDOG_RUNTIME.json'
SURV=ROOT/'tools/gate_btc_factory/SURVIVOR_HEALTH_RUNTIME.json'
OUT=ROOT/'tools/gate_btc_factory/SELF_AUDIT_RUNTIME.json'


def load(path: Path) -> dict:
    try:
        v=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise SystemExit(f'FAIL self audit cannot read {path.relative_to(ROOT)}: {exc}') from exc
    if not isinstance(v,dict): raise SystemExit(f'FAIL self audit expected object: {path.relative_to(ROOT)}')
    return v


def load_runtime(path: str) -> dict | None:
    try:
        raw=subprocess.check_output(
            ['git','show',f'origin/gate-btc-runtime:{path}'],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        v=json.loads(raw)
    except Exception as exc:
        raise SystemExit(f'FAIL self audit malformed runtime authority {path}: {exc}') from exc
    if not isinstance(v,dict):
        raise SystemExit(f'FAIL self audit expected runtime object: {path}')
    return v


def d50_qualification_healthy(row: dict | None) -> bool:
    if not row:
        return False
    dq=row.get('data_qualification',{})
    mirror=row.get('mirror_alignment',{})
    return (
        isinstance(dq,dict)
        and dq.get('qualified') is True
        and int(dq.get('current',0) or 0) >= int(dq.get('target',7) or 7)
        and isinstance(mirror,dict)
        and str(mirror.get('status','')).startswith('PASS_')
    )


def main() -> int:
    src=load(SOURCE); plan=load(PLAN); watch=load(WATCH); surv=load(SURV)
    tracks=src.get('tracks',{})
    b3=tracks.get('B3_H40_PLUS',{}) if isinstance(tracks,dict) else {}
    frontier=load_runtime('runtime/autonomous_science/CURRENT.json')
    d50=load_runtime('runtime/ledgers/d50/STATUS.json')
    h1=load_runtime('runtime/ledgers/b3_h1/STATUS.json')
    h31=load_runtime('runtime/ledgers/b3_h31_prospective/STATUS.json')
    momentum=load_runtime('runtime/ledgers/momentum_m1_m2/STATUS.json')
    v16b=load_runtime('runtime/ledgers/v16b/STATUS.json')

    blockers=[]
    for name,row in sorted(tracks.items()):
        if not isinstance(row,dict) or not row.get('blocker'):
            continue
        # A reconciled runtime qualification supersedes stale static D50 diagnostics.
        if name == 'D50_DATA_QUALIFICATION' and d50_qualification_healthy(d50):
            continue
        blockers.append({'track':name,'blocker':row.get('blocker')})

    runtime_authority={
        'B3_H1': {
            'status': h1.get('status') if h1 else None,
            'observations': h1.get('valid_observation_count') if h1 else None,
            'latest_date': h1.get('latest_valid_date') if h1 else None,
        },
        'B3_H31': {
            'status': h31.get('status') if h31 else None,
            'observations': h31.get('eligible_observations') if h31 else None,
            'latest_date': h31.get('latest_date') if h31 else None,
        },
        'MOMENTUM_M1_M2': {
            'status': momentum.get('status') if momentum else None,
            'observations': momentum.get('observed_snapshots') if momentum else None,
            'latest_date': momentum.get('data_as_of') if momentum else None,
        },
        'D50_DATA_QUALIFICATION': {
            'status': d50.get('data_qualification',{}).get('status') if d50 else None,
            'observations': d50.get('data_qualification',{}).get('current') if d50 else None,
            'target': d50.get('data_qualification',{}).get('target') if d50 else None,
            'qualified': d50.get('data_qualification',{}).get('qualified') if d50 else None,
        },
        'V16B': {
            'status': v16b.get('status') if v16b else None,
            'observations': v16b.get('canonical_cycle_count') if v16b else None,
            'latest_date': v16b.get('data_as_of') if v16b else None,
        },
    }
    report={
        'schema':'qrds.factory.self_audit.v2',
        'generated_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'frontier_status': frontier.get('status') if frontier else b3.get('status'),
        'frontier_generation': frontier.get('generation') if frontier else b3.get('canonical_active_generation'),
        'frontier_next_generation_start': frontier.get('next_generation_start') if frontier else None,
        'frontier_authority': 'gate-btc-runtime' if frontier else 'static_fallback',
        'active_generation_open_issue': b3.get('open_issue'),
        'active_generation_open_pr': b3.get('open_pr'),
        'planned_actions': plan.get('actions',[]),
        'stalled_tracks': watch.get('stalled_tracks',[]),
        'survivor_health_count': len(surv.get('survivors',[])),
        'transitions_allowed': plan.get('transitions_allowed'),
        'source_freshness': plan.get('source_freshness'),
        'runtime_authority': runtime_authority,
        'next_expected_action': (
            plan.get('actions',[{}])[0].get('action') if plan.get('actions') else
            ('OPERATIONAL_REPAIR' if watch.get('stalled_tracks') else 'MONITOR')
        ),
        'scientific_blockers':blockers,
        'safety':{
            'research_only':True,'shadow_only':True,'orders':0,'real_capital':0,
            'engine_feed':False,'backfill_allowed':False,'scientific_change_allowed':False,
        },
    }
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'frontier':report['frontier_generation'],'next':report['next_expected_action'],'stalled':report['stalled_tracks']},sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
