#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, io, json, time
from pathlib import Path
import requests

OUT=Path('artifacts/b3_h90_h99/B3_H90_H99_SOURCE_QA.json')
SERIES=['BAMLH0A0HYM2','BAMLC0A0CM','DFII10','T10YIE','DTWEXBGS','SOFR','DFF']
BASE='https://fred.stlouisfed.org/graph/fredgraph.csv?id={}'
START='2020-01-01'; END='2026-08-09'

def get(url):
    errs=[]
    for i in range(3):
        try:
            r=requests.get(url,timeout=(10,45),headers={'User-Agent':'QRDS-B3-H90-SourceQA/1.0'})
            return r,errs
        except (requests.Timeout,requests.ConnectionError) as e:
            errs.append(type(e).__name__+': '+str(e)[:160]); time.sleep(2*(i+1))
    return None,errs

def inspect(series):
    url=BASE.format(series)
    r,errs=get(url)
    if r is None:
        return {'series':series,'status':'DATA_GAP_TRANSIENT_DELIVERY','url':url,'errors':errs}
    raw=r.content
    row={'series':series,'url':url,'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'errors':errs}
    if r.status_code!=200:
        return {**row,'status':'DATA_GAP_HTTP'}
    try:
        text=raw.decode('utf-8-sig'); rd=csv.DictReader(io.StringIO(text)); rows=list(rd)
    except Exception as e:
        return {**row,'status':'DATA_GAP_SCHEMA','error':str(e)[:200]}
    if not rows or 'DATE' not in (rd.fieldnames or []) or series not in (rd.fieldnames or []):
        return {**row,'status':'DATA_GAP_SCHEMA','fields':rd.fieldnames}
    filt=[]
    seen=set(); dup=0; missing=0
    for x in rows:
        d=x.get('DATE',''); v=x.get(series,'')
        if START<=d<=END:
            if d in seen: dup+=1
            seen.add(d)
            if v in ('','.','NA','NaN'): missing+=1
            else: filt.append((d,v))
    years=sorted({d[:4] for d,_ in filt})
    status='PASS_SOURCE_QA' if filt and '2020' in years and '2024' in years and dup==0 else 'DATA_GAP_COVERAGE'
    return {**row,'status':status,'rows_nonmissing':len(filt),'missing_rows':missing,'duplicate_dates':dup,'first_date':filt[0][0] if filt else None,'last_date':filt[-1][0] if filt else None,'years':years}

def main():
    items=[inspect(s) for s in SERIES]
    passed=[x['series'] for x in items if x['status']=='PASS_SOURCE_QA']
    fam={
      'H90':'DATA_READY' if 'BAMLH0A0HYM2' in passed else 'DATA_GAP',
      'H91':'DATA_READY' if 'BAMLC0A0CM' in passed else 'DATA_GAP',
      'H92':'DATA_READY' if 'BAMLH0A0HYM2' in passed else 'DATA_GAP',
      'H93':'DATA_READY' if 'DFII10' in passed else 'DATA_GAP',
      'H94':'DATA_READY' if 'T10YIE' in passed else 'DATA_GAP',
      'H95':'DATA_READY' if 'DTWEXBGS' in passed else 'DATA_GAP',
      'H96':'DATA_READY' if all(s in passed for s in ['SOFR','DFF']) else 'DATA_GAP',
      'H97':'DATA_READY' if all(s in passed for s in ['BAMLH0A0HYM2','DFII10']) else 'DATA_GAP',
      'H98':'DATA_READY' if all(s in passed for s in ['BAMLH0A0HYM2','BAMLC0A0CM','DTWEXBGS','SOFR','DFF']) else 'DATA_GAP',
      'H99':'DATA_READY' if all(s in passed for s in ['BAMLH0A0HYM2','DFII10','DTWEXBGS']) else 'DATA_GAP'}
    out={'schema':'qrds.b3.h90_h99.source_qa.v1','source_provider':'Federal Reserve/FRED public CSV','cutoff_exclusive':'2026-08-10','series':items,'families':fam,'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'passed_series':passed,'families':fam},sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
