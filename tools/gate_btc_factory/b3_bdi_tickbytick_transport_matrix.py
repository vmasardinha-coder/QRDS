#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from typing import Any
import requests

HOST='https://arquivos.b3.com.br'
KEY='TickByTickDerivatives'
SCHEMA='qrds.factory.b3_bdi_tickbytick_transport_matrix.v1'


def sha(raw: bytes): return hashlib.sha256(raw).hexdigest() if raw else None


def run_probe(session: requests.Session, probe_date: str) -> dict[str, Any]:
    iso=probe_date
    y,m,d=iso.split('-')
    variants=[
        ('iso_1000_json', f'{HOST}/bdi/table/{KEY}/{iso}/{iso}/1/1000', 'json'),
        ('iso_100_json', f'{HOST}/bdi/table/{KEY}/{iso}/{iso}/1/100', 'json'),
        ('iso_1000_raw', f'{HOST}/bdi/table/{KEY}/{iso}/{iso}/1/1000', 'raw'),
        ('dmy_1000_json', f'{HOST}/bdi/table/{KEY}/{d}-{m}-{y}/{d}-{m}-{y}/1/1000', 'json'),
        ('compact_1000_json', f'{HOST}/bdi/table/{KEY}/{y}{m}{d}/{y}{m}{d}/1/1000', 'json'),
    ]
    rows=[]
    headers={'User-Agent':'QRDS-B3-BDI-source-qualification/1.0'}
    for name,url,mode in variants:
        try:
            if mode=='json':
                r=session.post(url, json={}, headers=headers, timeout=60)
            else:
                r=session.post(url, data=b'{}', headers={**headers,'Content-Type':'application/json'}, timeout=60)
            raw=r.content
            obj=None
            try: obj=r.json() if raw else None
            except Exception: pass
            rows.append({'variant':name,'url':url,'http_status':int(r.status_code),'response_bytes':len(raw),'sha256':sha(raw),'json_object':isinstance(obj,dict),'content_type':r.headers.get('content-type')})
        except Exception as exc:
            rows.append({'variant':name,'url':url,'error':f'{type(exc).__name__}: {exc}','response_bytes':0})
    positives=[x for x in rows if 200 <= int(x.get('http_status') or 0) < 300 and int(x.get('response_bytes') or 0)>0]
    return {
        'schema':SCHEMA,'provider':'B3','table_key':KEY,'probe_date':probe_date,'variants':rows,
        'physical_variant_count':len(positives),'strict_source_gate_green':False,'source_gate_credit':0,
        'historical_backfill_credit':0,'prospective_credit':0,'economics_read':False,
        'status':'BDI_SPECIAL_TRANSPORT_VARIANT_OBSERVED_NEEDS_QUALIFICATION' if positives else 'BDI_SPECIAL_TRANSPORT_NOT_RESOLVED_FAIL_CLOSED',
        'safety':{'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'fail_closed':True,'h1_economics_read':False}
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--date',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    out=run_probe(requests.Session(),a.date); p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'status':out['status'],'source_gate_green':False})); return 0

if __name__=='__main__': raise SystemExit(main())
