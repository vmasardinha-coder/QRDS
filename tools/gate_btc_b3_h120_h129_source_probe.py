#!/usr/bin/env python3
from __future__ import annotations
import hashlib,io,json,re,time,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import requests
OUT=Path('artifacts/b3_h120_h129/B3_H120_H129_SOURCE_QA.json')
BASE='https://www.b3.com.br/pesquisapregao/download?filelist=PR{date}.zip'
DATES=['2020-01-03','2020-07-01','2021-01-04','2021-07-01','2022-01-03','2023-01-03','2024-01-02','2025-01-03','2026-08-07']
PREFIXES=('WIN','WDO')
FUTURE_RE=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ][0-9]{2}$')
FIELDS=('TckrSymb','TradQty','RglrTraddCtrcts','FinInstrmQty','OpnIntrst','FrstPric','MinPric','MaxPric','LastPric')
def local(t):return t.rsplit('}',1)[-1]
def get(s,u):
 e=[]
 for i in range(1,4):
  try:return s.get(u,timeout=(10,45)),e
  except requests.RequestException as x:
   e.append({'attempt':i,'error':type(x).__name__+': '+str(x)[:180]})
   if i<3:time.sleep(i*2)
 return None,e
def xml_from(body):
 with zipfile.ZipFile(io.BytesIO(body)) as z:
  for m in [x for x in z.infolist() if not x.is_dir()]:
   b=z.read(m)
   if zipfile.is_zipfile(io.BytesIO(b)):
    with zipfile.ZipFile(io.BytesIO(b)) as q:
     for n in [x for x in q.infolist() if not x.is_dir()]:
      x=q.read(n)
      if n.filename.lower().endswith('.xml') or x.lstrip().startswith(b'<'):return n.filename,x,hashlib.sha256(b).hexdigest()
   if m.filename.lower().endswith('.xml') or b.lstrip().startswith(b'<'):return m.filename,b,None
 raise RuntimeError('NO_XML')
def scan(raw):
 f={x:0 for x in FIELDS};p={x:0 for x in PREFIXES};c={x:0 for x in PREFIXES};samples=[]
 for _,e in ET.iterparse(io.BytesIO(raw),events=('end',)):
  t=local(e.tag)
  if t in f:f[t]+=1
  if t=='TckrSymb':
   v=(e.text or '').strip().upper()
   for x in PREFIXES:
    if v.startswith(x):p[x]+=1
   m=FUTURE_RE.fullmatch(v)
   if m:
    c[m.group(1)]+=1
    if len(samples)<20:samples.append(v)
  e.clear()
 return f,p,c,samples
def main():
 s=requests.Session();s.headers.update({'User-Agent':'Mozilla/5.0 QRDS-H120-SourceQA/1.0'});rows=[]
 for d in DATES:
  compact=d[2:4]+d[5:7]+d[8:10];u=BASE.format(date=compact);r,errs=get(s,u);rec={'date':d,'url':u,'errors':errs}
  if r is None:rec['status']='DATA_GAP_TRANSIENT_DELIVERY';rows.append(rec);continue
  rec.update({'http_status':r.status_code,'bytes':len(r.content),'raw_sha256':hashlib.sha256(r.content).hexdigest(),'content_type':r.headers.get('content-type')})
  try:
   n,x,inner=xml_from(r.content);fc,pc,cc,sm=scan(x);rec.update({'xml_name':n,'xml_sha256':hashlib.sha256(x).hexdigest(),'nested_zip_sha256':inner,'field_counts':fc,'prefix_counts':pc,'future_contract_counts':cc,'sample_tickers':sm})
   needed=fc['TckrSymb']>0 and fc['TradQty']>0 and fc['OpnIntrst']>0 and fc['MinPric']>0 and fc['MaxPric']>0 and (fc['RglrTraddCtrcts']>0 or fc['FinInstrmQty']>0) and all(cc[k]>0 for k in PREFIXES)
   rec['status']='PASS' if r.status_code==200 and needed else 'DATA_GAP_SCHEMA_OR_FIELDS'
  except Exception as e:rec['status']='DATA_GAP_PARSE';rec['parse_error']=type(e).__name__+': '+str(e)[:200]
  rows.append(rec)
 passed=[x for x in rows if x['status']=='PASS'];older=[x for x in rows if x['date']<'2022-01-01'];older_pass=[x for x in older if x['status']=='PASS']
 status='SOURCE_QA_READY_STRATIFIED' if len(passed)==len(rows) else 'SOURCE_QA_PARTIAL_DATA_GAP'
 p={'schema':'qrds.b3.h120_h129.source_qa.v1','status':status,'provider':'B3','source':'BVBG.086.01 full PriceReport PR{YYMMDD}.zip','contract_identity_regex':FUTURE_RE.pattern,'sample_dates':DATES,'passed':len(passed),'total':len(rows),'older_replication_dates_passed':len(older_pass),'older_replication_dates_total':len(older),'rows':rows,'economics_run':False,'h1_economics_read':False,'survivor_partial_economics_read':False,'cutoff_exclusive':'2026-08-10','orders':0,'real_capital':0,'engine_feed':False,'not_approved':True}
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(p,indent=2,ensure_ascii=False)+'\n');print(json.dumps({'status':status,'passed':len(passed),'total':len(rows),'older_passed':len(older_pass)},sort_keys=True))
if __name__=='__main__':main()
