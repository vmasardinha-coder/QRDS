#!/usr/bin/env python3
from __future__ import annotations

import hashlib, io, json, time, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

OUT = Path('artifacts/b3_h80_h89_pricereport/B3_H80_H89_PRICEREPORT_PROBE.json')
BASE = 'https://www.b3.com.br/pesquisapregao/download?filelist={name}{date}.zip'
DATES = ['2026-08-07', '2026-03-30', '2025-01-03']
REPORTS = ['SPRD', 'PR']
PREFIXES = ('WDO', 'DOL', 'WIN', 'IND', 'DI1')
FIELDS = {'TckrSymb','AdjstdQt','PrvsAdjstdQt','LastPric','FrstPric','MinPric','MaxPric','OpnIntrst','FinInstrmQty','TradQty','RglrTraddCtrcts'}

def bounded_get(session, url):
    errors=[]
    for attempt in range(1,4):
        try:
            r=session.get(url,timeout=(10,45))
            return r,errors
        except (requests.Timeout,requests.ConnectionError) as exc:
            errors.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:240]})
            if attempt<3: time.sleep(2*attempt)
    return None,errors

def local(tag):
    return tag.rsplit('}',1)[-1]

def summarize_xml(raw):
    ticker=None
    rows=[]
    field_counts={k:0 for k in FIELDS}
    prefix_counts={p:0 for p in PREFIXES}
    samples=[]
    try:
        for event, elem in ET.iterparse(io.BytesIO(raw), events=('end',)):
            t=local(elem.tag)
            if t in FIELDS:
                field_counts[t]+=1
            if t=='TckrSymb':
                ticker=(elem.text or '').strip().upper()
                for p in PREFIXES:
                    if ticker.startswith(p): prefix_counts[p]+=1
                if ticker.startswith(PREFIXES) and len(samples)<30:
                    samples.append(ticker)
            elem.clear()
        status='PASS_XML'
    except Exception as exc:
        status='FAIL_XML_PARSE'
        rows.append(type(exc).__name__+': '+str(exc)[:240])
    return {'status':status,'field_counts':field_counts,'prefix_counts':prefix_counts,'ticker_samples':samples,'errors':rows}

def inspect_zip(body):
    result={'zip_valid':False,'members':[],'xml':[]}
    try:
        with zipfile.ZipFile(io.BytesIO(body)) as z:
            members=[m for m in z.infolist() if not m.is_dir()]
            result['zip_valid']=True
            result['members']=[{'name':m.filename,'bytes':m.file_size} for m in members]
            for m in members[:20]:
                data=z.read(m)
                if m.filename.lower().endswith('.xml') or data.lstrip().startswith(b'<'):
                    s=summarize_xml(data)
                    s['name']=m.filename
                    s['sha256']=hashlib.sha256(data).hexdigest()
                    s['bytes']=len(data)
                    result['xml'].append(s)
    except Exception as exc:
        result['zip_error']=type(exc).__name__+': '+str(exc)[:240]
    return result

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-PriceReport-Probe/1.0'})
    rows=[]
    for d in DATES:
        compact=d[2:4]+d[5:7]+d[8:10]
        for report in REPORTS:
            url=BASE.format(name=report,date=compact)
            r,errs=bounded_get(s,url)
            rec={'date':d,'report':report,'url':url,'errors':errs}
            if r is None:
                rec['status']='DATA_GAP_TRANSIENT_DELIVERY'; rows.append(rec); continue
            body=r.content
            rec.update({'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
            rec['archive']=inspect_zip(body)
            rec['status']='PASS_SOURCE_ZIP' if r.status_code==200 and rec['archive'].get('zip_valid') else 'DATA_GAP_NOT_VALID_ZIP'
            rows.append(rec)
    usable=[r for r in rows if r.get('status')=='PASS_SOURCE_ZIP' and r.get('archive',{}).get('xml')]
    payload={
        'schema':'qrds.b3.h80_h89.pricereport_probe.v1',
        'status':'PASS_OFFICIAL_PRICEREPORT_SOURCE' if usable else 'DATA_GAP_OFFICIAL_PRICEREPORT_UNAVAILABLE',
        'provider':'B3',
        'source_contract':{
            'url_pattern':'https://www.b3.com.br/pesquisapregao/download?filelist={SPRD|PR}{YYMMDD}.zip',
            'reports':{'SPRD':'BVBG.187.01 simplified derivatives price report','PR':'BVBG.086.01 full price report'},
            'observed_fields_sought':sorted(FIELDS),
            'target_prefixes':list(PREFIXES),
            'derived_features_allowed_only_after_source_qa':True,
        },
        'dates_all_pre_cutoff':all(d<'2026-08-10' for d in DATES),
        'rows':rows,
        'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,
        'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,
        'orders':0,'real_capital':0,'engine_feed':False,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'status':payload['status'],'usable':[(x['report'],x['date'],x['bytes']) for x in usable]},ensure_ascii=False))
    return 0

if __name__=='__main__': raise SystemExit(main())
