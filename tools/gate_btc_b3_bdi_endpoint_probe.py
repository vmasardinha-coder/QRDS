#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
import requests

URLS=[
 'https://arquivos.b3.com.br/bdi/config.js',
 'https://arquivos.b3.com.br/bdi/static/js/main.e591a35328ff179145c0.js',
]
NEEDLES=['/bdi/download','downloadUrl','drp.b3.com.br','baseURL','baseUrl','axios','exportFromApi']
OUT=Path('artifacts/b3_bdi_endpoint_probe/B3_BDI_ENDPOINT_PROBE.json')

def contexts(text,needle,radius=1200):
    out=[]; start=0
    while True:
        i=text.find(needle,start)
        if i<0: break
        out.append(text[max(0,i-radius):min(len(text),i+len(needle)+radius)])
        start=i+len(needle)
        if len(out)>=12: break
    return out

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-BDI-Endpoint-Probe/1.0'})
    docs=[]
    for u in URLS:
        r=s.get(u,timeout=45); r.raise_for_status(); text=r.text
        docs.append({'url':u,'status':r.status_code,'bytes':len(r.content),'contexts':{n:contexts(text,n) for n in NEEDLES if n in text}})
    payload={'status':'PASS','docs':docs,'research_only':True,'shadow_only':True,'not_approved':True,'orders':0,'real_capital':0}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
