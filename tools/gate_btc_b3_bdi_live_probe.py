#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re,time
from urllib.parse import urljoin
from pathlib import Path
import requests

ROOT='https://arquivos.b3.com.br/bdi/tabelas?lang=pt-BR'
OUT=Path('artifacts/b3_bdi_probe/B3_BDI_LIVE_PROBE.json')
ATTEMPTS=3
TIMEOUT=30

def get_bounded(s,url):
    errs=[]
    for attempt in range(1,ATTEMPTS+1):
        try:
            r=s.get(url,timeout=TIMEOUT)
            return r,errs
        except (requests.Timeout,requests.ConnectionError) as exc:
            errs.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:300]})
            if attempt<ATTEMPTS: time.sleep(2*attempt)
    return None,errs

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-BDI-Probe/2.0'})
    r,root_errors=get_bounded(s,ROOT)
    if r is None:
        payload={
            'status':'DATA_GAP_TRANSIENT_DELIVERY','root_url':ROOT,'root_errors':root_errors,
            'scripts':[],'bundles':[],'candidates':[],
            'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
            'research_only':True,'shadow_only':True,'not_approved':True,
            'orders':0,'real_capital':0,'engine_feed':False,
        }
        OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(payload,ensure_ascii=False)); return 0
    if r.status_code!=200:
        payload={
            'status':'DATA_GAP_HTTP','root_url':r.url,'root_http_status':r.status_code,
            'root_bytes':len(r.content),'root_sha256':hashlib.sha256(r.content).hexdigest(),
            'scripts':[],'bundles':[],'candidates':[],
            'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
            'research_only':True,'shadow_only':True,'not_approved':True,
            'orders':0,'real_capital':0,'engine_feed':False,
        }
        OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
        print(json.dumps(payload,ensure_ascii=False)); return 0
    html=r.text
    scripts=[urljoin(r.url,x) for x in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I)]
    candidates=[]; bundles=[]
    pats=[r'https?://[^"\'\s)]+', r'/api/[^"\'\s)]+', r'[^"\']{0,100}(?:csv|download|export|tabelas|table)[^"\']{0,160}']
    for u in scripts[:12]:
        q,errs=get_bounded(s,u)
        if q is None:
            bundles.append({'url':u,'errors':errs}); continue
        rec={'url':u,'status':q.status_code,'bytes':len(q.content),'sha256':hashlib.sha256(q.content).hexdigest()}
        bundles.append(rec)
        if q.status_code!=200: continue
        text=q.text[:12_000_000]
        for p in pats:
            for m in re.findall(p,text,re.I):
                x=' '.join(str(m).split())
                if x not in candidates: candidates.append(x[:500])
    payload={
        'status':'PASS','root_url':r.url,'root_http_status':r.status_code,'root_bytes':len(r.content),
        'root_sha256':hashlib.sha256(r.content).hexdigest(),'root_errors':root_errors,
        'scripts':scripts,'bundles':bundles,'candidates':candidates[:700],
        'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
        'research_only':True,'shadow_only':True,'not_approved':True,
        'orders':0,'real_capital':0,'engine_feed':False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'root_http_status':r.status_code,'scripts':len(scripts),'bundles':len(bundles),'candidates':len(candidates)},ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
