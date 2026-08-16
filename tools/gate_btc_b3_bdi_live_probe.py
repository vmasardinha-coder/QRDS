#!/usr/bin/env python3
from __future__ import annotations
import json, re
from urllib.parse import urljoin
from pathlib import Path
import requests

ROOT='https://arquivos.b3.com.br/bdi/tabelas?lang=pt-BR'
OUT=Path('artifacts/b3_bdi_probe/B3_BDI_LIVE_PROBE.json')

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-BDI-Probe/1.0'})
    r=s.get(ROOT,timeout=15); r.raise_for_status()
    html=r.text
    scripts=[urljoin(r.url,x) for x in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I)]
    candidates=[]; bundles=[]
    pats=[r'https?://[^"\'\s)]+', r'/api/[^"\'\s)]+', r'[^"\']{0,100}(?:csv|download|export|tabelas|table)[^"\']{0,160}']
    for u in scripts[:8]:
        try:
            q=s.get(u,timeout=15)
            bundles.append({'url':u,'status':q.status_code,'bytes':len(q.content)})
            if q.status_code!=200: continue
            text=q.text[:8_000_000]
            for p in pats:
                for m in re.findall(p,text,re.I):
                    x=' '.join(str(m).split())
                    if x not in candidates: candidates.append(x[:400])
        except Exception as e:
            bundles.append({'url':u,'error':repr(e)})
    payload={'status':'PASS','root_url':r.url,'root_http_status':r.status_code,'root_bytes':len(r.content),'scripts':scripts,'bundles':bundles,'candidates':candidates[:500], 'research_only':True,'orders':0,'real_capital':0}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(payload,ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
