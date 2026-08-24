#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
from urllib.parse import urljoin
import requests

BASE='https://arquivos.b3.com.br'
URLS=[
 f'{BASE}/bdi/config.js',
 f'{BASE}/bdi/static/js/main.e591a35328ff179145c0.js',
]
NEEDLES=['/bdi/download','downloadUrl','serverUrl','drp.b3.com.br','baseURL','baseUrl','axios','exportFromApi','minDate']
OUT=Path('artifacts/b3_bdi_endpoint_probe/B3_BDI_ENDPOINT_PROBE.json')

def contexts(text,needle,radius=1600,limit=20):
    out=[]; start=0
    while True:
        i=text.find(needle,start)
        if i<0: break
        out.append(text[max(0,i-radius):min(len(text),i+len(needle)+radius)])
        start=i+len(needle)
        if len(out)>=limit: break
    return out

def extract_config(text):
    keys=['relativeUrl','downloadUrl','serverUrl','minDate','userId','clientId','exportFromApi']
    out={}
    for key in keys:
        m=re.search(rf'\b{re.escape(key)}\s*:\s*(\[[^\]]*\]|"[^"]*"|\'[^\']*\'|true|false|\d+)',text)
        if not m: continue
        raw=m.group(1).strip()
        if raw.startswith('['):
            vals=[int(x) for x in re.findall(r'\d+',raw)]
            out[key]=vals
        elif raw[:1] in {'"',"'"}:
            out[key]=raw[1:-1]
        elif raw in {'true','false'}:
            out[key]=(raw=='true')
        else:
            out[key]=int(raw)
    return out

def literal_paths(text):
    vals=set()
    for pat in [r'["\']([^"\']*/bdi/[^"\']*)["\']', r'["\'](/[^"\']*(?:download|export|table|arquivo)[^"\']*)["\']']:
        for v in re.findall(pat,text,re.I):
            if len(v)<=240:
                vals.add(v)
    return sorted(vals)

def call_contexts(text):
    found=[]
    patterns=[r'axios\s*\.\s*(get|post|request)\s*\(',r'\.\s*(get|post)\s*\(',r'downloadUrl',r'/bdi/download']
    for pat in patterns:
        for m in re.finditer(pat,text,re.I):
            frag=text[max(0,m.start()-900):min(len(text),m.start()+1900)]
            if any(k in frag for k in ['download','export','table','tabela','serverUrl']):
                found.append(frag)
            if len(found)>=30: break
        if len(found)>=30: break
    return found

def probe_readonly(session,url):
    out={'url':url}
    for method in ('HEAD','OPTIONS','GET'):
        try:
            r=session.request(method,url,timeout=30,allow_redirects=False)
            out[method.lower()]={
                'status':r.status_code,
                'content_type':r.headers.get('content-type'),
                'allow':r.headers.get('allow'),
                'location':r.headers.get('location'),
                'bytes':len(r.content),
                'first_200':r.text[:200] if method=='GET' else None,
            }
        except Exception as exc:
            out[method.lower()]={'error':type(exc).__name__+': '+str(exc)[:240]}
    return out

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-BDI-Endpoint-Probe/2.0'})
    docs=[]; config={}; paths=set(); calls=[]
    for u in URLS:
        r=s.get(u,timeout=45); r.raise_for_status(); text=r.text
        sha=hashlib.sha256(r.content).hexdigest()
        if u.endswith('config.js'):
            config=extract_config(text)
        paths.update(literal_paths(text))
        calls.extend(call_contexts(text))
        docs.append({
            'url':u,'status':r.status_code,'bytes':len(r.content),'sha256':sha,
            'content_type':r.headers.get('content-type'),
            'contexts':{n:contexts(text,n) for n in NEEDLES if n in text},
        })
    download_path=config.get('downloadUrl') or '/bdi/download'
    download_url=urljoin(BASE,download_path)
    payload={
        'status':'PASS',
        'docs':docs,
        'config_contract':config,
        'literal_paths':sorted(paths),
        'download_call_contexts':calls[:30],
        'readonly_endpoint_probe':probe_readonly(s,download_url),
        'economics_run':False,
        'h1_economics_read':False,
        'survivor_partial_economics_read':False,
        'research_only':True,'shadow_only':True,'not_approved':True,
        'orders':0,'real_capital':0,'engine_feed':False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({
        'status':payload['status'],
        'config_contract':config,
        'literal_paths_count':len(paths),
        'download_contexts':len(calls),
        'readonly_probe':payload['readonly_endpoint_probe'],
    },ensure_ascii=False))
    return 0
if __name__=='__main__': raise SystemExit(main())
