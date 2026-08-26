#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'tools/gate_btc_research_factory_status.json'
REGISTRY=ROOT/'tools/gate_btc_factory/PROSPECTIVE_ACTIVATIONS.json'
OUT=ROOT/'tools/gate_btc_factory/SURVIVOR_HEALTH_RUNTIME.json'
APPROVAL_PREFIXES=('APPROVED_FOR_SEPARATE_PROSPECTIVE','APPROVED_PROSPECTIVE')


def load(path: Path) -> dict:
    try:
        v=json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        raise SystemExit(f'FAIL survivor health cannot read {path.relative_to(ROOT)}: {exc}') from exc
    if not isinstance(v,dict): raise SystemExit('FAIL survivor health expected object')
    return v


def main() -> int:
    src=load(SOURCE); reg=load(REGISTRY)
    acts=reg.get('activations',{}) if isinstance(reg.get('activations',{}),dict) else {}
    rows=[]
    for name,row in sorted(src.get('tracks',{}).items()):
        if not isinstance(row,dict): continue
        status=str(row.get('status',''))
        approved=status.startswith(APPROVAL_PREFIXES)
        if not approved and row.get('classification')!='SURVIVOR_MONITORING': continue
        activation=acts.get(name,{}) if isinstance(acts.get(name,{}),dict) else {}
        rows.append({
            'track':name,
            'approval_status':status,
            'activation_state':activation.get('state'),
            'prospective_count':row.get('prospective_count'),
            'last_snapshot':row.get('last_snapshot'),
            'last_success_at':row.get('last_success_at'),
            'next_expected_run':row.get('next_expected_run'),
            'blocker':row.get('blocker'),
            'operational_repair_allowed': True if approved else False,
            'scientific_change_allowed': False,
        })
    OUT.write_text(json.dumps({
        'schema':'qrds.factory.survivor_health.v1',
        'generated_at_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
        'survivors':rows,
        'safety':{'orders':0,'real_capital':0,'engine_feed':False,'backfill_allowed':False,'scientific_change_allowed':False},
    },indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f'SURVIVOR_HEALTH_COUNT={len(rows)}')
    return 0

if __name__=='__main__': raise SystemExit(main())
