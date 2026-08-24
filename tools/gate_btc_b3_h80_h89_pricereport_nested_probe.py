#!/usr/bin/env python3
from __future__ import annotations
import hashlib, io, json, time, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

OUT=Path('artifacts/b3_h80_h89_pricereport_nested/B3_H80_H89_PRICEREPORT_NESTED_PROBE.json')
BASE='https://www.b3.com.br/pesquisapregao/download?filelist={prefix}{date}.zip'
DATES=['2026-08-07','2026-03-30','2025-01-03']
REPORTS=['SPRD','PR']
PREFIXES=('WDO','DOL','WIN','IND','DI1')
FIELDS=('TckrSymb','AdjstdQt','PrvsAdjstdQt','LastPric','FrstPric','MinPric','MaxPric','OpnIntrst','FinInstrmQty','TradQty','RglrTraddCtrcts')

def local(tag): return tag.rsplit('}',1)[-1]

def fetch(s,url):
    errs=[]
    for attempt in range(1,4):
        try: return s.get(url,timeout=(10,45)),errs
        except (requests.Timeout,requests.ConnectionError) as exc:
            errs.append({'attempt':attempt,'error':type(exc).__name__+': '+str(exc)[:180]})
            if attempt<3: time.sleep(2*attempt)
    return None,errs

def xml_summary(raw):
    fc={k:0 for k in FIELDS}; pc={p:0 for p in PREFIXES}; samples=[]
    for _,e in ET.iterparse(io.BytesIO(raw),events=('end',)):
        t=local(e.tag)
        if t in fc: fc[t]+=1
        if t=='TckrSymb':
            v=(e.text or '').strip().upper()
            for p in PREFIXES:
                if v.startswith(p): pc[p]+=1
            if v.startswith(PREFIXES) and len(samples)<20: samples.append(v)
        e.clear()
    return {'field_counts':fc,'prefix_counts':pc,'ticker_samples':samples}

def inspect(body):
    out={'outer_sha256':hashlib.sha256(body).hexdigest(),'outer_bytes':len(body),'inner':[]}
    with zipfile.ZipFile(io.BytesIO(body)) as outer:
        for m in [x for x in outer.infolist() if not x.is_dir()][:10]:
            b=outer.read(m)
            rec={'name':m.filename,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
            xml_payloads=[]
            if zipfile.is_zipfile(io.BytesIO(b)):
                with zipfile.ZipFile(io.BytesIO(b)) as inner:
                    rec['nested_members']=[x.filename for x in inner.infolist() if not x.is_dir()][:20]
                    for n in [x for x in inner.infolist() if not x.is_dir()][:20]:
                        x=inner.read(n)
                        if n.filename.lower().endswith('.xml') or x.lstrip().startswith(b'<'):
                            xml_payloads.append((n.filename,x))
            elif m.filename.lower().endswith('.xml') or b.lstrip().startswith(b'<'):
                xml_payloads.append((m.filename,b))
            rec['xml']=[]
            for name,x in xml_payloads:
                sm=xml_summary(x); sm.update({'name':name,'bytes':len(x),'sha256':hashlib.sha256(x).hexdigest()}); rec['xml'].append(sm)
            out['inner'].append(rec)
    return out

def main():
    s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 GATE-BTC-H80-PR-Nested/1.0'})
    rows=[]
    for d in DATES:
        ds=d[2:4]+d[5:7]+d[8:10]
        for prefix in REPORTS:
            url=BASE.format(prefix=prefix,date=ds); r,errs=fetch(s,url)
            rec={'date':d,'report':prefix,'url':url,'errors':errs}
            if r is None:
                rec['status']='DATA_GAP_TRANSIENT_DELIVERY'; rows.append(rec); continue
            rec.update({'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest()})
            try:
                rec['archive']=inspect(r.content)
                xmls=[x for a in rec['archive']['inner'] for x in a.get('xml',[])]
                rec['target_prefix_counts']={p:sum(x['prefix_counts'].get(p,0) for x in xmls) for p in PREFIXES}
                rec['field_counts']={f:sum(x['field_counts'].get(f,0) for x in xmls) for f in FIELDS}
                rec['status']='PASS_SOURCE_XML' if xmls and sum(rec['target_prefix_counts'].values())>0 else 'DATA_GAP_NO_TARGET_XML'
            except Exception as exc:
                rec['status']='DATA_GAP_ARCHIVE_PARSE'; rec['parse_error']=type(exc).__name__+': '+str(exc)[:220]
            rows.append(rec)
    usable=[r for r in rows if r.get('status')=='PASS_SOURCE_XML']
    payload={'schema':'qrds.b3.h80_h89.pricereport_nested_probe.v1','status':'PASS_OFFICIAL_PRICEREPORT_SOURCE' if usable else 'DATA_GAP_OFFICIAL_PRICEREPORT_UNAVAILABLE','provider':'B3','dates_all_pre_cutoff':all(d<'2026-08-10' for d in DATES),'rows':rows,'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'cutoff_exclusive':'2026-08-10','research_only':True,'shadow_only':True,'not_approved':True,'orders':0,'real_capital':0,'engine_feed':False}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':payload['status'],'usable':[(r['report'],r['date'],r.get('target_prefix_counts')) for r in usable]},ensure_ascii=False))
if __name__=='__main__': main()
