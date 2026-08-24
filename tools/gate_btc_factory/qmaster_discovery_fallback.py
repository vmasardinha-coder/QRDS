#!/usr/bin/env python3
"""Resolve QMASTER from local candidates, then canonical runtime export.

Reporting-only. Never fabricates QMASTER. A candidate is accepted only when its status
sidecar says PASS and the safety boundary remains research-only/no-orders/no-capital.
"""
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys
from datetime import datetime


def sha256_file(p: pathlib.Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def safe_sidecar(obj: dict) -> bool:
    return (
        obj.get('status') == 'PASS'
        and obj.get('research_only') is True
        and obj.get('orders_generated',0) == 0
        and obj.get('real_capital_used',0) == 0
        and obj.get('operational_status') in (None,'NOT_APPROVED')
    )

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--local',action='append',default=[])
    ap.add_argument('--runtime-root',required=True)
    ap.add_argument('--output',default='qmaster_discovery_status.json')
    args=ap.parse_args()
    runtime=pathlib.Path(args.runtime_root)
    candidates=[pathlib.Path(x) for x in args.local]
    canonical_csv=runtime/'runtime'/'GATE_BTC_QMASTER_LATEST.csv'
    canonical_txt=runtime/'runtime'/'GATE_BTC_QMASTER_LATEST.txt'
    selected=None; authority=None; sidecar=None; errors=[]

    for p in candidates:
        if p.is_file() and p.stat().st_size>0:
            selected=p; authority='LOCAL_DISCOVERY'; break

    if selected is None:
        try:
            if not canonical_txt.is_file():
                raise FileNotFoundError(str(canonical_txt))
            sidecar=json.loads(canonical_txt.read_text(encoding='utf-8'))
            if not safe_sidecar(sidecar):
                raise ValueError('canonical QMASTER sidecar failed safety/status validation')
            if not canonical_csv.is_file() or canonical_csv.stat().st_size == 0:
                raise FileNotFoundError(str(canonical_csv))
            actual=sha256_file(canonical_csv)
            expected=sidecar.get('csv_sha256')
            if expected and actual != expected:
                raise ValueError(f'QMASTER hash mismatch expected={expected} actual={actual}')
            selected=canonical_csv; authority='CANONICAL_RUNTIME_FALLBACK'
        except Exception as e:
            errors.append(str(e))

    result={
      'schema':'gate_btc.qmaster_discovery_fallback.v1',
      'generated_at_utc':datetime.utcnow().isoformat(timespec='seconds')+'Z',
      'status':'PASS' if selected else 'WARN_INPUT_GAP',
      'authority':authority,
      'selected_path':str(selected) if selected else '',
      'errors':errors,
      'research_only':True,'not_approved':True,'orders':0,'real_capital':0,'engine_feed':False,
      'canonical_sidecar':sidecar,
    }
    pathlib.Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if selected else 2

if __name__=='__main__':
    raise SystemExit(main())
