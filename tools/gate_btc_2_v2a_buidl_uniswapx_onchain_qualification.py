#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered BUIDL/USDC UniswapX settlements.

Blockscout is used only as a public index of the same Ethereum ledger. Scientific
identity remains exact BUIDL + USDC + frozen official UniswapX reactor set.
"""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

BUIDL='0x7712c34205737192402172409a8f7ccef8aa2aec'
USDC='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
REACTORS={x.lower() for x in ['0x00000011F84B9aa48e5f8aA8B9897600006289Be','0x0000000015757c461808EA25Eb309638B62681cf','0x6000da47483062A0D734Ba3dc7576Ce6A0B645C4']}
BASE='https://eth.blockscout.com/api/v2'
START=date(2026,8,4); END=date(2026,9,5); UA='QRDS-GateBTC2-ResearchOnly/1'
ATTEMPTS=[]

def get_json(url,retries=6):
    last=None
    for n in range(retries):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
            with urllib.request.urlopen(req,timeout=90) as r: raw=r.read()
            obj=json.loads(raw); ATTEMPTS.append({'url':url,'result':'PASS','sha256':hashlib.sha256(raw).hexdigest()})
            return raw,obj
        except Exception as exc:
            last=exc; ATTEMPTS.append({'url':url,'result':'FAIL','error':f'{type(exc).__name__}:{exc}'})
            time.sleep(min(16,2**n))
    raise RuntimeError(f'BLOCKSCOUT_FAILED:{last}')

def iso_day(value):
    if not value:return None
    return datetime.fromisoformat(str(value).replace('Z','+00:00')).astimezone(timezone.utc).date()

def addr(x):
    if isinstance(x,dict):return str(x.get('hash') or '').lower()
    return str(x or '').lower()

def amount(item):
    total=item.get('total') or {}; raw=total.get('value'); dec=total.get('decimals')
    if raw is None:return 0.0
    try:return int(str(raw))/(10**int(dec or 0))
    except Exception:return 0.0

def token_addr(item):
    return str((item.get('token') or {}).get('address_hash') or '').lower()

def paginate_buidl_transfers():
    url=f'{BASE}/tokens/{BUIDL}/transfers'; rows=[]; hashes=[]; complete=False
    for _ in range(200):
        raw,obj=get_json(url); hashes.append(hashlib.sha256(raw).hexdigest()); items=obj.get('items') or []; rows.extend(items)
        days=[iso_day(x.get('timestamp')) for x in items if x.get('timestamp')]
        if days and min(days)<START: complete=True; break
        nxt=obj.get('next_page_params')
        if not nxt: complete=True; break
        url=f'{BASE}/tokens/{BUIDL}/transfers?{urllib.parse.urlencode(nxt)}'
    if not complete: raise RuntimeError('BLOCKSCOUT_TRANSFER_HISTORY_NOT_EXHAUSTED_BEFORE_FROZEN_START')
    return rows,hashes

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args(); out=a.output_dir; out.mkdir(parents=True,exist_ok=True)
    error=None; fills=[]; candidates=[]; raw_hashes=[]; transfers=[]; history_complete=False
    try:
        transfers,raw_hashes=paginate_buidl_transfers(); history_complete=True
        txids=sorted({str(x.get('transaction_hash') or '') for x in transfers if x.get('transaction_hash') and iso_day(x.get('timestamp')) and START<=iso_day(x.get('timestamp'))<=END})
        for txh in txids:
            traw,tx=get_json(f'{BASE}/transactions/{txh}'); xraw,xobj=get_json(f'{BASE}/transactions/{txh}/token-transfers'); raw_hashes += [hashlib.sha256(traw).hexdigest(),hashlib.sha256(xraw).hexdigest()]
            status=str(tx.get('status') or '').lower(); to=addr(tx.get('to')); reactor_link=to in REACTORS
            items=xobj.get('items') or []
            b=[x for x in items if token_addr(x)==BUIDL and amount(x)>0]
            u=[x for x in items if token_addr(x)==USDC and amount(x)>0]
            candidates.append({'tx_hash':txh,'status':status,'to':to,'reactor_link':reactor_link,'buidl_transfers':len(b),'usdc_transfers':len(u)})
            if status not in {'ok','success'} or not reactor_link or len(b)!=1 or len(u)!=1: continue
            day=iso_day(tx.get('timestamp'))
            if not day or not START<=day<=END: continue
            bamt=amount(b[0]); uamt=amount(u[0])
            if bamt<=0 or uamt<=0: continue
            ts=int(datetime.fromisoformat(str(tx['timestamp']).replace('Z','+00:00')).timestamp())
            fills.append({'tx_hash':txh,'timestamp':ts,'day':day.isoformat(),'buidl':bamt,'usdc':uamt,'price_usdc_per_buidl':uamt/bamt})
        days=defaultdict(list)
        for f in fills:days[f['day']].append(f)
        daily=[]
        for d,rs in sorted(days.items()):
            rs=sorted(rs,key=lambda x:x['timestamp']); px=[x['price_usdc_per_buidl'] for x in rs]
            daily.append({'day':d,'open':px[0],'high':max(px),'low':min(px),'close':px[-1],'volume_buidl':sum(x['buidl'] for x in rs),'trade_count':len(rs)})
        have={x['day'] for x in daily}; missing=[]
        cur=START
        from datetime import timedelta
        while cur<=END:
            if cur.isoformat() not in have:missing.append(cur.isoformat())
            cur+=timedelta(days=1)
        qa=bool(fills) and len(daily)==33 and not missing and all(x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high'] and x['volume_buidl']>=0 for x in daily)
        status='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION' if qa else ('FAIL_CLOSED_NO_PHYSICAL_UNISWAPX_FILLS' if not fills else 'FAIL_CLOSED_FULL_CORPUS_QA')
    except Exception as exc:
        error=str(exc); daily=[]; missing=[]; qa=False; status='FAIL_CLOSED_SOURCE_OR_PARSE'
    for name,obj in [('FILLS.json',fills),('DAILY_OHLCV.json',daily),('CANDIDATES.json',candidates),('BLOCKSCOUT_ATTEMPTS.json',ATTEMPTS)]:
        (out/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    s={'schema_version':'GATE_BTC_2_V2A_BUIDL_UNISWAPX_ONCHAIN_QUALIFICATION_V6_BLOCKSCOUT_LEDGER_INDEX','symbol':'BUIDL','provider':'UNISWAPX_ETHEREUM_DIRECT_CHAIN','ledger_index_transport':'BLOCKSCOUT_PUBLIC_API_V2','blockscout_base':BASE,'buidl_contract':BUIDL,'usdc_contract':USDC,'reactors':sorted(REACTORS),'requested_start_utc':START.isoformat(),'requested_end_utc':END.isoformat(),'history_complete_to_before_start':history_complete,'indexed_buidl_transfer_count':len(transfers),'reactor_linked_candidates':sum(1 for x in candidates if x['reactor_link']),'physical_fill_count':len(fills),'daily_bucket_count':len(daily),'missing_days':missing,'raw_response_sha256':raw_hashes,'qa_pass':qa,'status':status,'error':error,'qualification_only':True,'source_admitted':False,'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders_generated':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True}
    (out/'SUMMARY.json').write_text(json.dumps(s,indent=2,sort_keys=True)+'\n'); print(json.dumps(s,sort_keys=True)); return 0

if __name__=='__main__': raise SystemExit(main())
