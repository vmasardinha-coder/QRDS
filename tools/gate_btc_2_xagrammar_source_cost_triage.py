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
        if env.get('fresh_namespace') != xid:
            raise RuntimeError(f'NAMESPACE_MISMATCH:{xid}')
        if env.get('economics_read') is not False:
            raise RuntimeError(f'ECONOMICS_ALREADY_READ:{xid}')
        if env.get('economic_credit') != 0:
            raise RuntimeError(f'ECONOMIC_CREDIT_NONZERO:{xid}')
        if env.get('status') != 'PREREGISTERED_NEXT_GATE_SOURCE_COST_QUALIFICATION':
            raise RuntimeError(f'UNEXPECTED_PREREG_STATUS:{xid}:{env.get("status")}')
        rows.append({
            'fresh_namespace':xid,
            'channel':frozen['channel'],
            'decision':frozen['decision'],
            'reason':frozen['reason'],
            'source_cost':frozen['source_cost'],
            'next_gate':frozen['next_gate'],
            'economics_read':False,
            'economic_credit':0,
            'promotion_authority':False,
        })

    counts=Counter(r['decision'] for r in rows)
    if dict(counts) != contract['expected_counts']:
        # expected also contains READY_FOR_ECONOMICS=0; normalize zeros explicitly.
        got={k:counts.get(k,0) for k in contract['expected_counts']}
        if got != contract['expected_counts']:
            raise RuntimeError(f'COUNT_MISMATCH:{got}')

    out={
        'schema':'gate_btc_2.xagrammar_source_cost_triage_runtime.v1',
        'status':'TRIAGE_COMPLETE_NO_ECONOMICS_OPENED',
        'input_count':len(rows),
        'counts':{k:counts.get(k,0) for k in contract['expected_counts']},
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
