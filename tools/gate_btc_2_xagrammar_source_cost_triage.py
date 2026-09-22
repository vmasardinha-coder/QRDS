#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--runtime-root', required=True)
    ap.add_argument('--contract', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()

    root=Path(args.runtime_root)
    contract=load(Path(args.contract))
    prereg_dir=root/'runtime/factory_autonomy/grammar_preregistrations'
    found={p.stem:load(p) for p in prereg_dir.glob('XAGRAMMAR_*.json')}
    expected=set(contract['decisions'])
    if set(found) != expected:
        raise RuntimeError(f'XAGRAMMAR_SET_MISMATCH expected={sorted(expected)} found={sorted(found)}')

    rows=[]
    for xid in sorted(expected):
        env=found[xid]
        frozen=contract['decisions'][xid]
        if env.get('family_id') != xid:
            raise RuntimeError(f'FAMILY_ID_MISMATCH:{xid}:{env.get("family_id")}')
        if env.get('channel_id') != frozen['channel']:
            raise RuntimeError(f'CHANNEL_MISMATCH:{xid}:{env.get("channel_id")}')
        if env.get('economics_read') is not False or env.get('historical_testing_started') is not False:
            raise RuntimeError(f'ECONOMICS_OR_TESTING_ALREADY_OPENED:{xid}')
        if env.get('existing_counter_credit') != 0 or env.get('prospective_credit') != 0:
            raise RuntimeError(f'CREDIT_NONZERO:{xid}')
        if env.get('status') != 'PREREGISTERED_AWAITING_SOURCE_COST_QUALIFICATION':
            raise RuntimeError(f'UNEXPECTED_PREREG_STATUS:{xid}:{env.get("status")}')
        if env.get('next_stage') != 'SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY':
            raise RuntimeError(f'UNEXPECTED_NEXT_STAGE:{xid}:{env.get("next_stage")}')
        if env.get('source_qualification_required') is not True or env.get('cost_applicability_required') is not True:
            raise RuntimeError(f'SOURCE_COST_GATE_NOT_REQUIRED:{xid}')
        rows.append({
            'family_id':xid,
            'grammar_signature':env.get('grammar_signature'),
            'channel':frozen['channel'],
            'decision':frozen['decision'],
            'reason':frozen['reason'],
            'source_cost':frozen['source_cost'],
            'next_gate':frozen['next_gate'],
            'economics_read':False,
            'historical_testing_started':False,
            'economic_credit':0,
            'promotion_authority':False,
        })

    counts=Counter(r['decision'] for r in rows)
    got={k:counts.get(k,0) for k in contract['expected_counts']}
    if got != contract['expected_counts']:
        raise RuntimeError(f'COUNT_MISMATCH:{got}')

    out={
        'schema':'gate_btc_2.xagrammar_source_cost_triage_runtime.v1',
        'status':'TRIAGE_COMPLETE_NO_ECONOMICS_OPENED',
        'input_count':len(rows),
        'counts':got,
        'ready_for_economics_count':0,
        'rows':rows,
        'policy':contract['policy'],
        'safety':contract['safety'],
    }
    p=Path(args.out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'status':out['status'],'counts':out['counts']},sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
