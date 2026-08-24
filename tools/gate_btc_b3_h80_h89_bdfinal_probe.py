#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, time, zipfile
from pathlib import Path
import requests

OUT=Path('artifacts/b3_h80_h89_bdfinal/B3_H80_H89_BDFINAL_SOURCE_QA.json')
BASE='https://www.b3.com.br/pesquisapregao/download?filelist={name}'
DATES=['2020-01-03','2020-07-01','2021-01-04','2021-07-01']
PREFIXES=('WDO','DOL','WIN','IND','DI1')

def candidates(d: str):
    yymmdd=d[2:4]+d[5:7]+d[8:10]
    yyyymmdd=d.replace('-','')
    return [
        f'BD_Final{yymmdd}.zip',
        f'BD_FINAL{yymmdd}.zip',
        f'BD{yymmdd}.zip',
        f'BD_Final{yyyymmdd}.zip',
        f'BD_FINAL{yyyymmdd}.zip',
        f'BD{yyyymmdd}.zip',
    ]

def get(session,url):
    errors=[]
    for attempt in range(1,4):
        try:
            r=session.get(url,timeout=(10,40),allow_redirects=True)
            return r,errors
        except (requests.Timeout,requests.ConnectionError) as exc:
            errors.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:180]})
            if attempt<3: time.sleep(2*attempt)
    return None,errors

def inspect_payload(body: bytes):
    if not zipfile.is_zipfile(io.BytesIO(body)):
        return {'zip':False,'members':[],'prefix_hits':{p:0 for p in PREFIXES}}
    members=[]; hits={p:0 for p in PREFIXES}
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        for info in [x for x in z.infolist() if not x.is_dir()]:
            raw=z.read(info)
            members.append({'name':info.filename,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
            text=raw.decode('latin-1','ignore').upper()
            for p in PREFIXES:
                hits[p]+=text.count(p)
    return {'zip':True,'members':members,'prefix_hits':hits}

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-BDFinal-QA/1.0'})
    rows=[]
    for d in DATES:
        attempts=[]; selected=None
        for name in candidates(d):
            url=BASE.format(name=name); r,errs=get(s,url)
            rec={'name':name,'url':url,'errors':errs}
            if r is None:
                rec['status']='DATA_GAP_TRANSIENT_DELIVERY'; attempts.append(rec); continue
            rec.update({'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()})
            inspection=inspect_payload(r.content)
            rec.update(inspection)
            useful=r.status_code==200 and inspection['zip'] and sum(inspection['prefix_hits'].values())>0
            rec['status']='PASS_CANDIDATE' if useful else 'NOT_MATCHING_LEGACY_FILE'
            attempts.append(rec)
            if useful:
                selected=rec; break
        rows.append({'date':d,'selected':selected,'attempts':attempts,'status':'PASS' if selected else 'DATA_GAP_LEGACY_REQUEST_CONTRACT'})
    passed=sum(1 for r in rows if r['status']=='PASS')
    payload={
        'schema':'qrds.b3.h80_h89.bdfinal_source_qa.v1',
        'source_provider':'B3',
        'source_description':'Derivatives Market - Exchange Market Trades - Final (BD_Final)',
        'status':'PASS_LEGACY_SOURCE_CONTRACT' if passed==len(rows) else 'DATA_GAP_LEGACY_REQUEST_CONTRACT',
        'sample_dates':DATES,'passed':passed,'total':len(rows),'rows':rows,
        'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
        'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,
        'orders':0,'real_capital':0,'engine_feed':False,
        'next_gate':'FREEZE_EXACT_FILENAME_SCHEMA_AND_FULL_2020_2021_COVERAGE_BEFORE_ECONOMICS' if passed else 'KEEP_DATA_GAP_AND_CONTINUE_OFFICIAL_SOURCE_DISCOVERY'
    }
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'passed':passed,'total':len(rows)},ensure_ascii=False))
if __name__=='__main__': main()
