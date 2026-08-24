#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, time, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

OUT=Path('artifacts/b3_h80_h89_pricereport_coverage/B3_H80_H89_PRICEREPORT_COVERAGE.json')
BASE='https://www.b3.com.br/pesquisapregao/download?filelist=SPRD{date}.zip'
DATES=['2020-01-03','2020-07-01','2021-01-04','2021-07-01','2022-01-03','2023-01-03','2024-01-02','2025-01-03','2026-08-07']
PREFIXES=('WDO','DOL','WIN','IND','DI1')
FIELDS=('TckrSymb','AdjstdQt','PrvsAdjstdQt','LastPric','OpnIntrst','AdjstdQtTax')

def local(tag): return tag.rsplit('}',1)[-1]

def get(s,url):
    errs=[]
    for attempt in range(1,4):
        try: return s.get(url,timeout=(10,40)),errs
        except (requests.Timeout,requests.ConnectionError) as exc:
            errs.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:180]})
            if attempt<3: time.sleep(2*attempt)
    return None,errs

def extract_xml(body):
    with zipfile.ZipFile(io.BytesIO(body)) as outer:
        members=[m for m in outer.infolist() if not m.is_dir()]
        for m in members:
            b=outer.read(m)
            if zipfile.is_zipfile(io.BytesIO(b)):
                with zipfile.ZipFile(io.BytesIO(b)) as inner:
                    for n in [x for x in inner.infolist() if not x.is_dir()]:
                        x=inner.read(n)
                        if n.filename.lower().endswith('.xml') or x.lstrip().startswith(b'<'):
                            return n.filename,x,hashlib.sha256(b).hexdigest()
            elif m.filename.lower().endswith('.xml') or b.lstrip().startswith(b'<'):
                return m.filename,b,None
    raise RuntimeError('NO_XML_PAYLOAD')

def summarize(raw):
    pc={p:0 for p in PREFIXES}; fc={f:0 for f in FIELDS}; sample=[]
    for _,e in ET.iterparse(io.BytesIO(raw),events=('end',)):
        t=local(e.tag)
        if t in fc: fc[t]+=1
        if t=='TckrSymb':
            v=(e.text or '').strip().upper()
            for p in PREFIXES:
                if v.startswith(p): pc[p]+=1
            if v.startswith(PREFIXES) and len(sample)<15: sample.append(v)
        e.clear()
    return pc,fc,sample

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-SPRD-Coverage/1.0'})
    rows=[]
    for d in DATES:
        ds=d[2:4]+d[5:7]+d[8:10]; url=BASE.format(date=ds); r,errs=get(s,url)
        rec={'date':d,'url':url,'errors':errs}
        if r is None:
            rec['status']='DATA_GAP_TRANSIENT_DELIVERY'; rows.append(rec); continue
        rec.update({'http_status':r.status_code,'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest(),'content_type':r.headers.get('content-type')})
        try:
            name,x,inner_sha=extract_xml(r.content); pc,fc,sample=summarize(x)
            rec.update({'xml_name':name,'xml_sha256':hashlib.sha256(x).hexdigest(),'inner_zip_sha256':inner_sha,'prefix_counts':pc,'field_counts':fc,'sample_tickers':sample})
            rec['status']='PASS' if r.status_code==200 and sum(pc.values())>0 and fc['TckrSymb']>0 else 'DATA_GAP_SCHEMA'
        except Exception as exc:
            rec['status']='DATA_GAP_PARSE'; rec['parse_error']=type(exc).__name__+': '+str(exc)[:200]
        rows.append(rec)
    passed=[r for r in rows if r.get('status')=='PASS']
    payload={'schema':'qrds.b3.h80_h89.pricereport_coverage_probe.v1','status':'PASS_STRATIFIED_2020_2026' if len(passed)==len(rows) else 'PARTIAL_STRATIFIED_COVERAGE','sample_dates':DATES,'passed':len(passed),'total':len(rows),'rows':rows,'next_gate':'FULL_SESSION_COVERAGE_AND_CAUSAL_INGESTION_REQUIRED_BEFORE_ECONOMICS','economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,'orders':0,'real_capital':0,'engine_feed':False}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'passed':payload['passed'],'total':payload['total']},ensure_ascii=False))
if __name__=='__main__': main()
