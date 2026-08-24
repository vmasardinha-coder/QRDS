#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,time
from pathlib import Path
import requests

BASE='https://arquivos.b3.com.br/bdi/table'
OUT=Path('artifacts/b3_h80_h89_tables/B3_H80_H89_TABLE_PROBE.json')
DATES=['2026-08-07','2026-03-30','2025-01-03']
TABLES=['InstrumentsDerivatives','ConsolidatedTradesDerivatives','OpenPositionsEquities','AnalyticalFramework2']

def get_bounded(s,url):
    errs=[]
    for attempt in range(1,4):
        try:
            r=s.get(url,headers={'Accept':'application/json,text/plain,*/*'},timeout=40)
            return r,errs
        except (requests.Timeout,requests.ConnectionError) as exc:
            errs.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:300]})
            if attempt<3: time.sleep(2*attempt)
    return None,errs

def shape(obj):
    if isinstance(obj,list):
        sample=obj[:3]
        keys=sorted({k for row in sample if isinstance(row,dict) for k in row})
        return {'type':'list','len':len(obj),'sample_keys':keys,'sample':sample}
    if isinstance(obj,dict):
        return {'type':'object','keys':sorted(obj)[:100],'sample':{k:obj[k] for k in list(obj)[:10]}}
    return {'type':type(obj).__name__,'value':obj}

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-Table-Probe/1.0'})
    rows=[]
    for date in DATES:
        for name in TABLES:
            url=f'{BASE}/{name}/{date}'
            r,errs=get_bounded(s,url)
            if r is None:
                rows.append({'table':name,'date':date,'url':url,'status':'DATA_GAP_TRANSIENT_DELIVERY','errors':errs}); continue
            body=r.content
            rec={'table':name,'date':date,'url':r.url,'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'errors':errs,'first_300':r.text[:300]}
            try: rec['json_shape']=shape(r.json())
            except Exception: rec['json_shape']=None
            rows.append(rec)
    usable=[r for r in rows if r.get('http_status')==200 and r.get('json_shape')]
    payload={
        'schema':'qrds.b3.h80_h89.table_probe.v1',
        'status':'PASS_TABLES_DISCOVERED' if usable else 'DATA_GAP_NO_USABLE_TABLES',
        'dates_all_pre_cutoff':all(d<'2026-08-10' for d in DATES),
        'rows':rows,
        'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
        'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,
        'orders':0,'real_capital':0,'engine_feed':False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'usable':[(r['table'],r['date'],r['json_shape']['type'],r['json_shape'].get('len')) for r in usable]},ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
