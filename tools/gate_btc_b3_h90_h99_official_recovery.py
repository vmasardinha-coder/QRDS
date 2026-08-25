#!/usr/bin/env python3
from __future__ import annotations

import hashlib, io, json, re, zipfile
from pathlib import Path
import requests
import xml.etree.ElementTree as ET

OUT=Path('artifacts/b3_h90_h99/B3_H90_H99_OFFICIAL_RECOVERY.json')
START='2020-01-01'; END='2026-08-09'
UA={'User-Agent':'QRDS-B3-H90-OfficialRecovery/1.0'}


def fetch(url, timeout=60):
    errs=[]
    for i in range(3):
        try:
            r=requests.get(url,timeout=(10,timeout),headers=UA)
            return r,errs
        except (requests.Timeout,requests.ConnectionError) as e:
            errs.append(type(e).__name__+': '+str(e)[:160])
    return None,errs


def sha(raw): return hashlib.sha256(raw).hexdigest()

def local(tag): return tag.rsplit('}',1)[-1].upper()

def parse_treasury_xml(raw):
    root=ET.fromstring(raw)
    rows=[]
    for node in root.iter():
        props={}
        for child in list(node):
            k=local(child.tag); v=(child.text or '').strip()
            if v: props[k]=v
        date=next((v for k,v in props.items() if 'DATE' in k and re.match(r'\d{4}-\d{2}-\d{2}',v)),None)
        ten=next((v for k,v in props.items() if '10YEAR' in k and re.match(r'^-?\d+(?:\.\d+)?$',v)),None)
        if date and ten and START<=date[:10]<=END:
            rows.append((date[:10],float(ten)))
    dedup={}
    dup=0
    for d,v in rows:
        if d in dedup: dup+=1
        dedup[d]=v
    return sorted(dedup.items()),dup


def treasury_series(kind):
    all_rows=[]; manifests=[]; dups=0
    for year in range(2020,2027):
        url=f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data={kind}&field_tdr_date_value={year}'
        r,errs=fetch(url)
        rec={'year':year,'url':url,'errors':errs}
        if r is None:
            rec['status']='DATA_GAP_TRANSIENT_DELIVERY'; manifests.append(rec); continue
        raw=r.content; rec.update(http_status=r.status_code,bytes=len(raw),sha256=sha(raw),content_type=r.headers.get('content-type'))
        if r.status_code!=200:
            rec['status']='DATA_GAP_HTTP'; manifests.append(rec); continue
        try: rows,dup=parse_treasury_xml(raw)
        except Exception as e:
            rec.update(status='DATA_GAP_SCHEMA',error=str(e)[:180]); manifests.append(rec); continue
        rec.update(status='PASS_YEAR' if rows else 'DATA_GAP_SCHEMA',rows=len(rows),first=rows[0][0] if rows else None,last=rows[-1][0] if rows else None,duplicate_dates=dup)
        manifests.append(rec); all_rows.extend(rows); dups+=dup
    merged=dict(all_rows); years=sorted({d[:4] for d in merged})
    status='PASS_SOURCE_QA' if '2020' in years and '2024' in years and dups==0 and len(merged)>=1000 else 'DATA_GAP_COVERAGE'
    return {'status':status,'rows':len(merged),'years':years,'manifests':manifests,'values':merged}


def nyfed(rate, secured):
    side='secured' if secured else 'unsecured'
    url=f'https://markets.newyorkfed.org/api/rates/{side}/{rate}/search.json?startDate=2020-01-01&endDate=2026-08-09&type=rate'
    r,errs=fetch(url)
    base={'url':url,'errors':errs}
    if r is None: return {**base,'status':'DATA_GAP_TRANSIENT_DELIVERY','values':{}}
    raw=r.content; base.update(http_status=r.status_code,bytes=len(raw),sha256=sha(raw),content_type=r.headers.get('content-type'))
    if r.status_code!=200: return {**base,'status':'DATA_GAP_HTTP','values':{}}
    try: obj=r.json()
    except Exception as e: return {**base,'status':'DATA_GAP_SCHEMA','error':str(e)[:180],'values':{}}
    candidates=[]
    def walk(x):
        if isinstance(x,dict):
            if any(k in x for k in ('effectiveDate','effective_date','date')) and any(k in x for k in ('percentRate','rate','percent_rate')): candidates.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x,list):
            for v in x: walk(v)
    walk(obj)
    vals={}
    for x in candidates:
        d=str(x.get('effectiveDate') or x.get('effective_date') or x.get('date') or '')[:10]
        v=x.get('percentRate',x.get('percent_rate',x.get('rate')))
        try: fv=float(v)
        except (TypeError,ValueError): continue
        if START<=d<=END: vals[d]=fv
    years=sorted({d[:4] for d in vals})
    status='PASS_SOURCE_QA' if '2020' in years and '2024' in years and len(vals)>=1000 else 'DATA_GAP_COVERAGE'
    return {**base,'status':status,'rows':len(vals),'years':years,'values':vals}


def h10_probe():
    url='https://www.federalreserve.gov/datadownload/Output.aspx?filetype=zip&rel=H10'
    r,errs=fetch(url,90)
    base={'url':url,'errors':errs}
    if r is None: return {**base,'status':'DATA_GAP_TRANSIENT_DELIVERY'}
    raw=r.content; base.update(http_status=r.status_code,bytes=len(raw),sha256=sha(raw),content_type=r.headers.get('content-type'))
    if r.status_code!=200: return {**base,'status':'DATA_GAP_HTTP'}
    try:
        z=zipfile.ZipFile(io.BytesIO(raw)); names=z.namelist()
        text='\n'.join(z.read(n).decode('utf-8','ignore') for n in names if n.lower().endswith(('.xml','.csv','.txt')))
    except Exception as e: return {**base,'status':'DATA_GAP_SCHEMA','error':str(e)[:180]}
    broad=('Broad Dollar' in text or 'BROAD DOLLAR' in text.upper())
    has2020=('2020-' in text or '2020/' in text); has2024=('2024-' in text or '2024/' in text)
    return {**base,'status':'PASS_SOURCE_SURFACE' if broad and has2020 and has2024 else 'DATA_GAP_COVERAGE','archive_members':len(names),'broad_dollar_marker':broad,'has_2020':has2020,'has_2024':has2024}


def main():
    real=treasury_series('daily_treasury_real_yield_curve')
    nominal=treasury_series('daily_treasury_yield_curve')
    common=sorted(set(real['values']) & set(nominal['values']))
    breakeven={d:nominal['values'][d]-real['values'][d] for d in common}
    be_years=sorted({d[:4] for d in breakeven})
    be_status='PASS_DERIVED_QA' if '2020' in be_years and '2024' in be_years and len(breakeven)>=1000 else 'DATA_GAP_COVERAGE'
    derived_raw='\n'.join(f'{d},{breakeven[d]:.8f}' for d in common).encode()
    sofr=nyfed('sofr',True); effr=nyfed('effr',False)
    liq_common=sorted(set(sofr.get('values',{})) & set(effr.get('values',{})))
    liq={d:sofr['values'][d]-effr['values'][d] for d in liq_common}
    liq_years=sorted({d[:4] for d in liq}); liq_status='PASS_DERIVED_QA' if '2020' in liq_years and '2024' in liq_years and len(liq)>=1000 else 'DATA_GAP_COVERAGE'
    h10=h10_probe()
    fam={
      'H90':'DATA_GAP_LICENSE_HISTORY','H91':'DATA_GAP_LICENSE_HISTORY','H92':'DATA_GAP_LICENSE_HISTORY',
      'H93':'DATA_READY' if real['status']=='PASS_SOURCE_QA' else 'DATA_GAP',
      'H94':'DATA_READY' if be_status=='PASS_DERIVED_QA' else 'DATA_GAP',
      'H95':'SOURCE_SURFACE_READY_NEEDS_EXACT_SERIES_PARSE' if h10['status']=='PASS_SOURCE_SURFACE' else 'DATA_GAP',
      'H96':'DATA_READY' if liq_status=='PASS_DERIVED_QA' else 'DATA_GAP',
      'H97':'DATA_GAP_DEPENDENCY_HY','H98':'DATA_GAP_DEPENDENCY_CREDIT','H99':'DATA_GAP_DEPENDENCY_HY'}
    out={'schema':'qrds.b3.h90_h99.official_recovery.v1','cutoff_exclusive':'2026-08-10','sources':{'treasury_real_10y':{k:v for k,v in real.items() if k!='values'},'treasury_nominal_10y':{k:v for k,v in nominal.items() if k!='values'},'nyfed_sofr':{k:v for k,v in sofr.items() if k!='values'},'nyfed_effr':{k:v for k,v in effr.items() if k!='values'},'fed_h10':h10},'derived':{'treasury_10y_breakeven':{'status':be_status,'rows':len(breakeven),'years':be_years,'sha256':sha(derived_raw),'formula':'nominal_10y_minus_real_10y'},'sofr_minus_effr':{'status':liq_status,'rows':len(liq),'years':liq_years,'sha256':sha(('\n'.join(f'{d},{liq[d]:.8f}' for d in liq_common)).encode()),'formula':'sofr_minus_effr'}},'families':fam,'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'families':fam,'real':real['status'],'breakeven':be_status,'liq':liq_status,'h10':h10['status']},sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
