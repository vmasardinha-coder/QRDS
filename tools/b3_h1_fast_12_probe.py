#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
import requests

DATE='2026-08-12'
URL=f'https://arquivos.b3.com.br/rapinegocios/tickercsv/{DATE}'
OUT=Path('artifacts/b3_h1_fast_12')
OUT.mkdir(parents=True,exist_ok=True)
rec={'schema':'gate_btc.b3.h1.fast_source_probe.v1','date':DATE,'url':URL,'research_only':True,'shadow_only':True,'economics_locked':True,'orders':0,'real_capital':0}
try:
    r=requests.get(URL,timeout=120,headers={'User-Agent':'Mozilla/5.0 B3 research v7 PhaseB blind automation','Accept':'*/*'})
    rec['http_status']=r.status_code; rec['bytes']=len(r.content); rec['content_type']=r.headers.get('content-type','')
    if r.status_code==200 and r.content[:2]==b'PK':
        p=OUT/f'{DATE}_NEGOCIOSAVISTA_original.zip'; p.write_bytes(r.content)
        rec['ok']=True; rec['sha256']=hashlib.sha256(r.content).hexdigest(); rec['path']=p.name
    else:
        rec['ok']=False
except Exception as e:
    rec['ok']=False; rec['error']=repr(e)
(OUT/'SOURCE_STATUS.json').write_text(json.dumps(rec,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(rec,indent=2,ensure_ascii=False))
raise SystemExit(0 if rec.get('ok') else 2)
