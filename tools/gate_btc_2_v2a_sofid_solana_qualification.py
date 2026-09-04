#!/usr/bin/env python3
"""Fail-closed exact-mint SOFID Solana qualifier via GeckoTerminal public data."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
BASE='https://api.geckoterminal.com/api/v2'; UA='QRDS-GateBTC2-ResearchOnly/1'; NETWORK='solana'; MINT='APhcqtzE73es3KAGiVksZFMLGwJDiAey5qZKUrQHEHfS'
def get(url,retries=4):
 last=None
 for n in range(retries):
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/json','Accept-Version':'20230302','User-Agent':UA})
   with urllib.request.urlopen(req,timeout=60) as r:return r.read()
  except Exception as e:last=e;time.sleep(2**n)
 raise RuntimeError(f'request failed: {last}')
def sh(x):return hashlib.sha256(x).hexdigest()
def dec(x):return json.loads(x.decode())
def tids(pool):
 rel=pool.get('relationships') or {};out=[]
 for side in ('base_token','quote_token'):
  rid=(((rel.get(side) or {}).get('data') or {}).get('id'))
  if rid:out.append(str(rid))
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--end',default='2026-09-02');ap.add_argument('--output',required=True);a=ap.parse_args();end=date.fromisoformat(a.end);start=end-timedelta(days=32);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 u=f'{BASE}/networks/{NETWORK}/tokens/{MINT}/pools?include=base_token,quote_token&page=1';pr=get(u);(out/'RAW_POOLS.json').write_bytes(pr);p=dec(pr);data=p.get('data') or [];mintlow=MINT.lower();hits=[]
 for idx,pool in enumerate(data):
  ids=tids(pool)
  if any(x.lower().endswith('_'+mintlow) or x.lower().endswith(mintlow) for x in ids):hits.append((idx,pool,ids))
 if not hits:
  result={'symbol':'SOFID','coin_id':'sofiusd','provider':'GECKOTERMINAL_PUBLIC_ONCHAIN','network':NETWORK,'token_contract':MINT,'qa_pass':False,'status':'FAIL_CLOSED_NO_EXACT_POOL','candidate_exact_pool_count':0,'sha256':{'pools':sh(pr)}}
 else:
  _,pool,ids=hits[0];pid=str(pool.get('id'));addr=pid.split('_',1)[-1];endts=int(datetime.combine(end+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1;q=urllib.parse.urlencode({'aggregate':1,'before_timestamp':endts,'limit':33,'currency':'usd','token':MINT});ou=f'{BASE}/networks/{NETWORK}/pools/{addr}/ohlcv/day?{q}';raw=get(ou);(out/'RAW_OHLCV.json').write_bytes(raw);payload=dec(raw);series=((((payload.get('data') or {}).get('attributes') or {}).get('ohlcv_list')) or []);rows=[]
  for x in series:
   if len(x)<6:continue
   ts=int(x[0]);d=datetime.fromtimestamp(ts,tz=timezone.utc).date()
   if d<start or d>end:continue
   op,hi,lo,cl,vol=map(float,x[1:6])
   if ts<=0 or vol<0 or (op==hi==lo==cl==0):continue
   if not(lo<=min(op,cl)<=max(op,cl)<=hi):raise ValueError('OHLC invariant failed')
   rows.append({'timestamp':ts,'day':d.isoformat(),'open':op,'high':hi,'low':lo,'close':cl,'volume':vol})
  rows.sort(key=lambda z:z['timestamp']);dup=len(rows)-len({z['timestamp'] for z in rows});mono=all(rows[i]['timestamp']<rows[i+1]['timestamp'] for i in range(len(rows)-1));have={z['day'] for z in rows};gaps=[];cur=start
  while cur<=end:
   if cur.isoformat() not in have:gaps.append(cur.isoformat())
   cur+=timedelta(days=1)
  qa=bool(rows) and dup==0 and mono and not gaps
  (out/'CANDLES.jsonl').write_text(''.join(json.dumps(z,sort_keys=True)+'\n' for z in rows))
  result={'symbol':'SOFID','coin_id':'sofiusd','provider':'GECKOTERMINAL_PUBLIC_ONCHAIN','network':NETWORK,'token_contract':MINT,'selected_pool_id':pid,'selected_pool_address':addr,'pool_relationship_token_ids':ids,'candidate_exact_pool_count':len(hits),'rows':len(rows),'earliest_day':rows[0]['day'] if rows else None,'latest_day':rows[-1]['day'] if rows else None,'duplicate_rows':dup,'monotonic':mono,'missing_days_in_requested_window':gaps,'qa_pass':qa,'status':'QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION' if qa else 'FAIL_CLOSED_FULL_CORPUS_QA','sha256':{'pools':sh(pr),'ohlcv':sh(raw)}}
 summary={'schema_version':'GATE_BTC_2_V2A_SOFID_SOLANA_PHYSICAL_V1','requested_start_utc':start.isoformat(),'requested_end_utc':end.isoformat(),'result':result,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True,'qualification_only':True,'source_admitted':False,'scientific_credit':False,'prospective_credit':False,'d0_credit':0}
 (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps(summary,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
