#!/usr/bin/env python3
import hashlib, json, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import date

BASE='https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml'
CUT=date(2026,8,10)
YEARS=range(2020,2027)
DATASETS={
 'nominal':('daily_treasury_yield_curve',('BC_3MONTH','BC_2YEAR','BC_10YEAR')),
 'real':('daily_treasury_real_yield_curve',('TC_5YEAR','TC_10YEAR')),
}

def lname(tag): return tag.rsplit('}',1)[-1]
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'QRDS-B3-research-source-qa/1.0'})
 with urllib.request.urlopen(req,timeout=30) as r:
  raw=r.read(); ctype=r.headers.get('content-type','')
 return raw,ctype

def parse(raw):
 root=ET.fromstring(raw)
 rows=[]
 for e in root.iter():
  if lname(e.tag)!='entry': continue
  row={}
  for x in e.iter():
   k=lname(x.tag); v=(x.text or '').strip()
   if v and len(list(x))==0: row[k]=v
  if row: rows.append(row)
 return rows

def find_key(keys,target):
 t=target.upper()
 exact=[k for k in keys if k.upper()==t]
 if exact: return exact[0]
 suffix=[k for k in keys if k.upper().endswith(t)]
 return suffix[0] if len(suffix)==1 else None

def main():
 report={'schema':'gate_btc.b3.h180_h189.treasury_source_qa.v1','cutoff_exclusive':'2026-08-10','provider':'U.S. Department of the Treasury','research_only':True,'orders':0,'real_capital':0,'engine_feed':False,'datasets':{},'status':'FAIL'}
 ok=True
 for label,(data_key,required) in DATASETS.items():
  ds={'data_key':data_key,'years':{},'required_fields':list(required)}; allkeys=set(); dates=[]
  for y in YEARS:
   url=f'{BASE}?data={data_key}&field_tdr_date_value={y}'
   try:
    raw,ctype=get(url); rows=parse(raw); sha=hashlib.sha256(raw).hexdigest()
   except Exception as ex:
    ds['years'][str(y)]={'url':url,'error':repr(ex)}; ok=False; continue
   keys=set().union(*(r.keys() for r in rows)) if rows else set(); allkeys|=keys
   datekey=find_key(keys,'NEW_DATE') or find_key(keys,'QUOTE_DATE') or find_key(keys,'DATE')
   valid_dates=[]
   if datekey:
    for r in rows:
     s=r.get(datekey,'')[:10]
     try:
      d=date.fromisoformat(s)
      if d<CUT: valid_dates.append(d.isoformat()); dates.append(d)
     except: pass
   ds['years'][str(y)]={'url':url,'sha256':sha,'content_type':ctype,'rows':len(rows),'date_field':datekey,'pre_cutoff_rows':len(valid_dates),'schema':sorted(keys)}
   if not rows or not datekey: ok=False
  missing=[f for f in required if not find_key(allkeys,f)]
  ds['missing_required_fields']=missing
  ds['coverage_min']=min(dates).isoformat() if dates else None
  ds['coverage_max_pre_cutoff']=max(dates).isoformat() if dates else None
  ds['duplicate_observation_dates']=len(dates)-len(set(dates))
  if missing or not dates or ds['duplicate_observation_dates']!=0: ok=False
  report['datasets'][label]=ds
 report['causal_availability_policy']='ONE_FULL_COMPLETED_B3_SESSION_LAG_UNLESS_PUBLICATION_TIMESTAMP_IS_INDEPENDENTLY_PROVEN'
 report['observed_vs_derived']={'nominal_yields':'OBSERVED_OFFICIAL','real_yields':'OBSERVED_OFFICIAL','nominal_minus_real_10y':'DERIVED_ONLY_AFTER_BOTH_CAUSAL'}
 report['status']='PASS' if ok else 'FAIL_CLOSED'
 print(json.dumps(report,indent=2,sort_keys=True))
 open('b3_h180_h189_treasury_source_qa.json','w').write(json.dumps(report,indent=2,sort_keys=True)+'\n')
 return 0 if ok else 2
if __name__=='__main__': sys.exit(main())
