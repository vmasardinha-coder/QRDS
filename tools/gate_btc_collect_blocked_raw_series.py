#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json,time,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
QUEUE=[('Huobi Token','HT','PRE','P1'),('Huobi Token','HTX','POST','P1'),('Zcoin','XZC','PRE','P1'),('Zcoin','FIRO','POST','P1'),('Kyber Legacy','KNCL','PRE','P1'),('Kyber','KNC','POST','P1'),('Ocean','OCEAN','PRE','P1'),('Ocean successor','FET','POST','P1'),('Ronin','RON','SINGLE','P1'),('ZKsync','ZK','SINGLE','P1'),('Movement','MOVE','SINGLE','P1'),('Oasis','ROSE','SINGLE','P1'),('Polymath','POLY','PRE','P1'),('Polymesh','POLYX','POST','P1'),('Stratis','STRAX','SPLIT','P1'),('dYdX Native','DYDX','SINGLE','P2'),('BitDAO','BIT','PRE','P2'),('Mantle','MNT','POST','P2'),('BinaryX','BNX','SPLIT','P2'),('MaidSafeCoin','MAID','PRE','P2'),('eMaidSafeCoin','EMAID','POST','P2'),('Syntropy','NOIA','PRE','P2'),('Syntropy successor','SYNT','POST','P2'),('Core','CORE','AMBIGUOUS','P3'),('Chain','XCN','AMBIGUOUS','P3'),('Acash Coin','ACH','AMBIGUOUS','P3'),('Beam','BEAM','AMBIGUOUS','P3'),('NXM','NXM','AMBIGUOUS','P3'),('Threshold','T','AMBIGUOUS','P3'),('WAX','WAXP','AMBIGUOUS','P3')]

def req(url):
 r=urllib.request.Request(url,headers={'User-Agent':'GATE-BTC-Research/1.0'})
 with urllib.request.urlopen(r,timeout=30) as f:return json.loads(f.read().decode())

def klines(symbol,start,end):
 out={};cursor=start
 while cursor<=end:
  q=urllib.parse.urlencode({'symbol':symbol,'interval':'1d','startTime':cursor,'endTime':end,'limit':1000})
  b=req('https://api.binance.com/api/v3/klines?'+q)
  if not b:break
  out.update({int(x[0]):x for x in b});n=int(b[-1][0])+86400000
  if n<=cursor:break
  cursor=n
  if len(b)<1000:break
  time.sleep(.2)
 return out

def write_csv(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not rows:path.write_text('',encoding='utf-8');return
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--start',default='2015-01-01');ap.add_argument('--end',default=datetime.now(timezone.utc).date().isoformat());ap.add_argument('--minimum-days',type=int,default=180);a=ap.parse_args()
 out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 start=int(datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc).timestamp()*1000);end=int(datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc).timestamp()*1000)+86399999
 btc=klines('BTCUSDT',start,end);btcclose={k:float(v[4]) for k,v in btc.items()};index=[];gaps=[]
 for name,ticker,leg,priority in QUEUE:
  folder=out/'raw_candidate_series'/f'{ticker}_{leg}';folder.mkdir(parents=True,exist_ok=True)
  pair=quote='';raw={};error=''
  for q in ('USDT','BUSD','USDC','BTC'):
   try:
    c=klines(ticker+q,start,end)
    if c:pair=ticker+q;quote=q;raw=c;break
   except Exception as e:error=str(e)
  rows=[]
  for ts,x in sorted(raw.items()):
   factor=btcclose.get(ts) if quote=='BTC' else 1.0
   if factor is None:continue
   rows.append({'date':datetime.fromtimestamp(ts/1000,tz=timezone.utc).date().isoformat(),'open_usd':float(x[1])*factor,'high_usd':float(x[2])*factor,'low_usd':float(x[3])*factor,'close_usd':float(x[4])*factor,'volume_base':float(x[5]),'quote_volume':float(x[7]),'source':'Binance spot','pair':pair})
  write_csv(folder/'daily_ohlcv.csv',rows);status='RAW_SERIES_AVAILABLE' if len(rows)>=a.minimum_days else 'BLOCKED_DATA'
  meta={'candidate_name':name,'ticker':ticker,'leg':leg,'priority':priority,'pair':pair,'rows':len(rows),'start_date':rows[0]['date'] if rows else None,'end_date':rows[-1]['date'] if rows else None,'collection_status':status,'error':error,'RAW_CANDIDATE_SERIES':True,'IDENTITY_CERTIFIED':False,'FORMAL_STATUS':'BLOCKED','CONVERSION_EVENT':'UNVERIFIED','CONTINUITY':'UNVERIFIED','RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'orders':0,'capital':0}
  (folder/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');(folder/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(folder.iterdir())),encoding='utf-8')
  index.append({'candidate':name,'ticker':ticker,'leg':leg,'priority':priority,'pair':pair,'rows':len(rows),'collection_status':status,'formal_status':'BLOCKED','identity_certified':False})
  if status!='RAW_SERIES_AVAILABLE':gaps.append({'candidate':name,'ticker':ticker,'reason':error or f'only {len(rows)} rows'})
 write_csv(out/'RAW_SERIES_INDEX.csv',index);write_csv(out/'UNRESOLVED_GAPS.csv',gaps)
 manifest={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'candidate_legs':len(index),'raw_series_available':sum(x['collection_status']=='RAW_SERIES_AVAILABLE' for x in index),'blocked_data':sum(x['collection_status']!='RAW_SERIES_AVAILABLE' for x in index),'formal_status_changes':0,'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'orders':0,'capital':0}
 (out/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');files=[p for p in out.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'];(out/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.relative_to(out)}\n' for p in sorted(files)),encoding='utf-8')
if __name__=='__main__':main()
