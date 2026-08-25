#!/usr/bin/env python3
from __future__ import annotations
import hashlib,io,json,re,zipfile
from pathlib import Path
import requests

OUT=Path('artifacts/b3_h90_h99/B3_H95_H10_EXACT_PROBE.json')
URL='https://www.federalreserve.gov/datadownload/Output.aspx?filetype=zip&rel=H10'


def main():
    r=requests.get(URL,timeout=(10,90),headers={'User-Agent':'QRDS-B3-H95-H10-Probe/1.0'})
    raw=r.content
    base={'url':URL,'http_status':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(raw),'archive_sha256':hashlib.sha256(raw).hexdigest()}
    if r.status_code!=200:
        out={**base,'status':'DATA_GAP_HTTP','economics_run':False,'h1_economics_read':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}; OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)); return 0
    try: z=zipfile.ZipFile(io.BytesIO(raw))
    except Exception as e:
        out={**base,'status':'DATA_GAP_SCHEMA','error':str(e)[:200],'economics_run':False,'h1_economics_read':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}; OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)); return 0
    members=[]; hits=[]; ids=set()
    for n in z.namelist():
        b=z.read(n); rec={'name':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
        members.append(rec)
        if not n.lower().endswith(('.xml','.csv','.txt')): continue
        text=b.decode('utf-8','ignore')
        for m in re.finditer(r'broad.{0,80}dollar|dollar.{0,80}broad',text,re.I|re.S):
            s=max(0,m.start()-500); e=min(len(text),m.end()+500); snippet=text[s:e].replace('\r',' ').replace('\n',' ')
            local_ids=set(re.findall(r'(?:SERIES_ID|SeriesID|SERIES_NAME|SeriesKey|SERIES)\s*[=:>"\']+\s*([A-Za-z0-9_.:-]{5,120})',snippet,re.I))
            local_ids.update(re.findall(r'H10/[A-Za-z0-9_.:-]+',snippet))
            ids.update(local_ids)
            hits.append({'member':n,'offset':m.start(),'snippet':snippet[:1400],'candidate_tokens':sorted(local_ids)})
    status='PASS_SCHEMA_DISCOVERY' if hits else 'DATA_GAP_SCHEMA'
    out={**base,'status':status,'members':members,'broad_dollar_hits':hits[:30],'candidate_series_tokens':sorted(ids),'hit_count':len(hits),'cutoff_exclusive':'2026-08-10','economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':status,'hits':len(hits),'tokens':sorted(ids)},sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
