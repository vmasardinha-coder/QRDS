#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, time
from pathlib import Path
import requests

BASE='https://arquivos.b3.com.br/bdi/table/export'
OUT=Path('artifacts/b3_h80_h89_export/B3_H80_H89_EXPORT_PROBE.json')
DATES=['2026-08-07','2026-03-30','2025-01-03']
TABLES=['InstrumentsDerivatives','ConsolidatedTradesDerivatives','OpenPositionsDerivatives','AnalyticalFramework2']
# Public client identifier published by official B3 BDI config.js; this is not a credential.
CLIENT_ID='5B34D25D-7044-4872-B8BA-28A5050CB7A6'

def post_bounded(s,payload):
    errs=[]
    for attempt in range(1,4):
        try:
            r=s.post(BASE,headers={'Accept':'application/json','Content-Type':'application/json'},json=payload,timeout=45)
            return r,errs
        except (requests.Timeout,requests.ConnectionError) as exc:
            errs.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:300]})
            if attempt<3: time.sleep(2*attempt)
    return None,errs

def shape(obj):
    if isinstance(obj,list):
        keys=sorted({k for row in obj[:5] if isinstance(row,dict) for k in row})
        return {'type':'list','len':len(obj),'sample_keys':keys,'sample':obj[:2]}
    if isinstance(obj,dict):
        out={'type':'object','keys':sorted(obj)[:100]}
        for k,v in obj.items():
            if isinstance(v,list):
                out.setdefault('lists',{})[k]={'len':len(v),'sample_keys':sorted({kk for row in v[:5] if isinstance(row,dict) for kk in row})}
        return out
    return {'type':type(obj).__name__}

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-Export-Probe/1.1'})
    rows=[]
    for date in DATES:
        for name in TABLES:
            # Official ASP.NET validation says Filters is IDictionary<string,object>, so the
            # frontend contract must send an object rather than an array. ClientId is the
            # public value exposed by B3 config.js. This is source-contract repair only.
            payload={'Name':name,'Date':date,'FinalDate':date,'ClientId':CLIENT_ID,'Filters':{}}
            r,errs=post_bounded(s,payload)
            if r is None:
                rows.append({'table':name,'date':date,'status':'DATA_GAP_TRANSIENT_DELIVERY','errors':errs}); continue
            body=r.content
            rec={'table':name,'date':date,'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'errors':errs,'first_300':r.text[:300]}
            try: rec['json_shape']=shape(r.json())
            except Exception: rec['json_shape']=None
            rows.append(rec)
    usable=[r for r in rows if r.get('http_status')==200 and r.get('json_shape') and r['json_shape'].get('type') in {'list','object'} and r.get('bytes',0)>2]
    payload={
      'schema':'qrds.b3.h80_h89.export_probe.v1',
      'status':'PASS_EXPORT_CONTRACT' if usable else 'DATA_GAP_EXPORT_CONTRACT_NOT_USABLE',
      'contract':{'method':'POST','url':BASE,'body_fields':['Name','Date','FinalDate','ClientId','Filters'],'filters_type':'object','client_id_source':'official B3 config.js public clientId','source':'official B3 frontend bundle + server validation contract'},
      'dates_all_pre_cutoff':all(d<'2026-08-10' for d in DATES),
      'rows':rows,
      'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
      'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,
      'orders':0,'real_capital':0,'engine_feed':False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'usable':[(r['table'],r['date'],r.get('json_shape')) for r in usable]},ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
