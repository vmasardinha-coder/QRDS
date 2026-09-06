#!/usr/bin/env python3
"""Fail-closed direct-chain qualifier for preregistered BUIDL/USDC UniswapX settlements."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
RPC_CANDIDATES=('https://ethereum-rpc.publicnode.com','https://eth.llamarpc.com','https://eth.drpc.org','https://1rpc.io/eth')
BUIDL='0x7712c34205737192402172409a8f7ccef8aa2aec'; USDC='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
REACTORS={x.lower() for x in ['0x00000011F84B9aa48e5f8aA8B9897600006289Be','0x0000000015757c461808EA25Eb309638B62681cf','0x6000da47483062A0D734Ba3dc7576Ce6A0B645C4']}
TRANSFER='0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'; START=date(2026,8,4); END=date(2026,9,5); UA='QRDS-GateBTC2-ResearchOnly/1'
ACTIVE_RPC=None; TRANSPORT_ATTEMPTS=[]
def raw_call(rpc,method,params,retries=3):
 body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params},separators=(',',':')).encode(); last=None
 for n in range(retries):
  try:
   req=urllib.request.Request(rpc,data=body,headers={'Content-Type':'application/json','User-Agent':UA}); raw=urllib.request.urlopen(req,timeout=90).read(); x=json.loads(raw)
   if x.get('error'): raise RuntimeError(json.dumps(x['error'],sort_keys=True))
   return raw,x.get('result')
  except Exception as e: last=e; time.sleep(min(4,2**n))
 raise RuntimeError(f'{type(last).__name__}:{last}')
def select_rpc():
 global ACTIVE_RPC
 if ACTIVE_RPC:return ACTIVE_RPC
 for rpc in RPC_CANDIDATES:
  try:
   raw_call(rpc,'eth_blockNumber',[],2); TRANSPORT_ATTEMPTS.append({'rpc':rpc,'probe':'PASS'}); ACTIVE_RPC=rpc; return rpc
  except Exception as e: TRANSPORT_ATTEMPTS.append({'rpc':rpc,'probe':'FAIL','error':str(e)})
 raise RuntimeError('ALL_PUBLIC_ETHEREUM_RPC_PROBES_FAILED')
def call(method,params):
 rpc=select_rpc()
 try:return raw_call(rpc,method,params,3)
 except Exception as first:
  # Same public Ethereum ledger, same frozen query. Rotate transport only; never source/identity/semantics.
  global ACTIVE_RPC; TRANSPORT_ATTEMPTS.append({'rpc':rpc,'method':method,'result':'FAIL','error':str(first)}); ACTIVE_RPC=None
  for alt in RPC_CANDIDATES:
   if alt==rpc:continue
   try:
    raw,res=raw_call(alt,method,params,3); ACTIVE_RPC=alt; TRANSPORT_ATTEMPTS.append({'rpc':alt,'method':method,'result':'PASS'}); return raw,res
   except Exception as e: TRANSPORT_ATTEMPTS.append({'rpc':alt,'method':method,'result':'FAIL','error':str(e)})
  raise RuntimeError(f'RPC_FAILED_ALL_TRANSPORTS:{method}')
def block(n): _,x=call('eth_getBlockByNumber',[hex(n),False]); return x
def block_for(ts):
 _,latest=call('eth_blockNumber',[]); lo,hi=1,int(latest,16)
 while lo<hi:
  mid=(lo+hi)//2; bt=int(block(mid)['timestamp'],16); lo=mid+1 if bt<ts else lo; hi=hi if bt<ts else mid
 return lo
def topic_addr(t): return '0x'+str(t)[-40:].lower()
def decode_transfer(log):
 if len(log.get('topics') or [])<3:return None
 try:return {'token':str(log['address']).lower(),'from':topic_addr(log['topics'][1]),'to':topic_addr(log['topics'][2]),'amount':int(log['data'],16)}
 except Exception:return None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=True);error=None;candidates=[];fills=[];raw_hashes=[]
 try:
  s_ts=int(datetime.combine(START,datetime.min.time(),tzinfo=timezone.utc).timestamp());e_ts=int(datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1;sb=block_for(s_ts);eb=block_for(e_ts);logs=[]
  for left in range(sb,eb+1,10000):
   right=min(eb,left+9999);raw,res=call('eth_getLogs',[{'fromBlock':hex(left),'toBlock':hex(right),'address':BUIDL,'topics':[TRANSFER]}]);raw_hashes.append(hashlib.sha256(raw).hexdigest());logs.extend(res or [])
  for h in sorted({str(x.get('transactionHash')) for x in logs if x.get('transactionHash')}):
   rr,rec=call('eth_getTransactionReceipt',[h]);rt,tx=call('eth_getTransactionByHash',[h]);raw_hashes += [hashlib.sha256(rr).hexdigest(),hashlib.sha256(rt).hexdigest()]
   if not rec or rec.get('status')!='0x1':continue
   reactor_link=(str((tx or {}).get('to') or '').lower() in REACTORS) or any(str(l.get('address') or '').lower() in REACTORS for l in rec.get('logs') or [])
   if not reactor_link:continue
   trs=[decode_transfer(l) for l in rec.get('logs') or [] if str(l.get('topics',[None])[0] if l.get('topics') else '').lower()==TRANSFER];trs=[x for x in trs if x and x['token'] in {BUIDL,USDC}];b=[x for x in trs if x['token']==BUIDL and x['amount']>0];u=[x for x in trs if x['token']==USDC and x['amount']>0];candidates.append({'tx_hash':h,'buidl_transfers':len(b),'usdc_transfers':len(u),'reactor_link':True})
   if len(b)!=1 or len(u)!=1:continue
   ts=int(block(int(rec['blockNumber'],16))['timestamp'],16);d=datetime.fromtimestamp(ts,timezone.utc).date();bamt=b[0]['amount']/1e6;uamt=u[0]['amount']/1e6
   if START<=d<=END and bamt>0 and uamt>0:fills.append({'tx_hash':h,'timestamp':ts,'day':d.isoformat(),'buidl':bamt,'usdc':uamt,'price_usdc_per_buidl':uamt/bamt})
  days=defaultdict(list)
  for f in fills:days[f['day']].append(f)
  daily=[]
  for d,rs in sorted(days.items()):
   rs=sorted(rs,key=lambda x:x['timestamp']);px=[x['price_usdc_per_buidl'] for x in rs];daily.append({'day':d,'open':px[0],'high':max(px),'low':min(px),'close':px[-1],'volume_buidl':sum(x['buidl'] for x in rs),'trade_count':len(rs)})
  have={x['day'] for x in daily};missing=[];cur=START
  while cur<=END:
   if cur.isoformat() not in have:missing.append(cur.isoformat())
   cur+=timedelta(days=1)
  qa=bool(fills) and len(daily)==33 and not missing and all(x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high'] for x in daily);status='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION' if qa else ('FAIL_CLOSED_NO_PHYSICAL_UNISWAPX_FILLS' if not fills else 'FAIL_CLOSED_FULL_CORPUS_QA')
 except Exception as e:error=str(e);sb=eb=None;logs=[];fills=[];daily=[];missing=[];qa=False;status='FAIL_CLOSED_SOURCE_OR_PARSE'
 for name,obj in [('FILLS.json',fills),('DAILY_OHLCV.json',daily),('CANDIDATES.json',candidates),('TRANSPORT_ATTEMPTS.json',TRANSPORT_ATTEMPTS)]: (out/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
 s={'schema_version':'GATE_BTC_2_V2A_BUIDL_UNISWAPX_ONCHAIN_QUALIFICATION_V2_TRANSPORT_EXHAUSTION','symbol':'BUIDL','provider':'UNISWAPX_ETHEREUM_DIRECT_CHAIN','ethereum_rpc_transport':ACTIVE_RPC,'rpc_transport_candidates':list(RPC_CANDIDATES),'transport_attempts':TRANSPORT_ATTEMPTS,'buidl_contract':BUIDL,'usdc_contract':USDC,'reactors':sorted(REACTORS),'start_block':sb,'end_block':eb,'buidl_transfer_logs':len(logs),'reactor_linked_candidates':len(candidates),'physical_fill_count':len(fills),'daily_bucket_count':len(daily),'missing_days':missing,'rpc_response_sha256':raw_hashes,'qa_pass':qa,'status':status,'error':error,'qualification_only':True,'source_admitted':False,'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders_generated':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True};(out/'SUMMARY.json').write_text(json.dumps(s,indent=2,sort_keys=True)+'\n');print(json.dumps(s,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
