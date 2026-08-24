#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
import requests

BASE='https://arquivos.b3.com.br/bdi'
OUT=Path('artifacts/b3_h80_h89_catalog/B3_H80_H89_BDI_CATALOG.json')
ENDPOINTS=[
    ('classifications',f'{BASE}/table/classifications'),
    ('all_tables',f'{BASE}/table/all'),
    ('workdays',f'{BASE}/table/workdays?date=2026-08-07'),
]

def get_bounded(s,url):
    errors=[]
    for attempt in range(1,4):
        try:
            r=s.get(url,headers={'Accept':'application/json,text/plain,*/*'},timeout=35)
            return r,errors
        except (requests.Timeout,requests.ConnectionError) as exc:
            errors.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:300]})
            if attempt<3: time.sleep(2*attempt)
    return None,errors

def summarize_json(obj):
    if isinstance(obj,dict):
        out={'type':'object','keys':sorted(obj)[:100]}
        for k,v in obj.items():
            if isinstance(v,list): out.setdefault('lists',{})[k]={'len':len(v),'sample':v[:5]}
        return out
    if isinstance(obj,list):
        return {'type':'list','len':len(obj),'sample':obj[:10]}
    return {'type':type(obj).__name__,'value':obj}

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-Catalog/1.0'})
    rows=[]
    for name,url in ENDPOINTS:
        r,errors=get_bounded(s,url)
        if r is None:
            rows.append({'name':name,'url':url,'status':'DATA_GAP_TRANSIENT_DELIVERY','errors':errors}); continue
        body=r.content
        rec={
            'name':name,'url':r.url,'http_status':r.status_code,'bytes':len(body),
            'sha256':hashlib.sha256(body).hexdigest(),'content_type':r.headers.get('content-type'),
            'errors':errors,'first_500':r.text[:500],
        }
        try:
            rec['json_summary']=summarize_json(r.json())
        except Exception:
            rec['json_summary']=None
        rows.append(rec)
    usable=[r for r in rows if r.get('http_status')==200 and r.get('json_summary')]
    payload={
        'schema':'qrds.b3.h80_h89.bdi_catalog.v1',
        'status':'PASS_CATALOG_DISCOVERED' if usable else 'DATA_GAP_NO_JSON_CATALOG',
        'rows':rows,
        'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
        'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,
        'orders':0,'real_capital':0,'engine_feed':False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'usable':[r['name'] for r in usable]},ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
