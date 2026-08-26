#!/usr/bin/env python3
from __future__ import annotations

import json
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


def main() -> int:
    src=load(SOURCE); plan=load(PLAN); watch=load(WATCH); surv=load(SURV)
    tracks=src.get('tracks',{})
    b3=tracks.get('B3_H40_PLUS',{}) if isinstance(tracks,dict) else {}
    report={
        'schema':'qrds.factory.self_audit.v1',
        'generated_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'frontier_status': b3.get('status'),
        'active_generation_open_issue': b3.get('open_issue'),
        'active_generation_open_pr': b3.get('open_pr'),
        'planned_actions': plan.get('actions',[]),
        'stalled_tracks': watch.get('stalled_tracks',[]),
        'survivor_health_count': len(surv.get('survivors',[])),
        'transitions_allowed': plan.get('transitions_allowed'),
        'source_freshness': plan.get('source_freshness'),
        'next_expected_action': (
            plan.get('actions',[{}])[0].get('action') if plan.get('actions') else
            ('OPERATIONAL_REPAIR' if watch.get('stalled_tracks') else 'MONITOR')
        ),
        'scientific_blockers':[{
            'track':name,'blocker':row.get('blocker')
        } for name,row in sorted(tracks.items()) if isinstance(row,dict) and row.get('blocker')],
        'safety':{
            'research_only':True,'shadow_only':True,'orders':0,'real_capital':0,
            'engine_feed':False,'backfill_allowed':False,'scientific_change_allowed':False,
        },
    }
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'next':report['next_expected_action'],'stalled':report['stalled_tracks']},sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
