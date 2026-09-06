#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BUIDL='0x7712c34205737192402172409a8f7ccef8aa2aec'
USDC='0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
CHAIN_ID=1
END=date(2026,9,5)
START=END-timedelta(days=32)
UA='QRDS-GateBTC2-ResearchOnly/1'


def req(url:str)->bytes:
    r=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':UA})
    with urllib.request.urlopen(r,timeout=90) as resp:return resp.read()

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def norm(a:str)->str:return str(a or '').lower()

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); args=ap.parse_args()
    out=args.output_dir; out.mkdir(parents=True,exist_ok=True)
    pair=f'{BUIDL}-{USDC}-{CHAIN_ID}'
    query=urllib.parse.urlencode({'pair':pair,'orderStatus':'filled','limit':50})
    url='https://api.uniswap.org/v2/orders?'+query
    error=None; raw=b''; orders=[]; valid=[]
    try:
        raw=req(url); (out/'RAW_UNISWAPX_ORDERS.json').write_bytes(raw); payload=json.loads(raw)
        orders=payload.get('orders',[]) if isinstance(payload,dict) else []
        if not isinstance(orders,list): raise ValueError('orders envelope mismatch')
        for o in orders:
            if not isinstance(o,dict) or str(o.get('orderStatus','')).lower()!='filled': continue
            tx=str(o.get('txHash') or '')
            fill_ts=o.get('fillTimestamp')
            if not tx.startswith('0x') or len(tx)!=66 or fill_ts is None: continue
            ts=int(fill_ts); d=datetime.fromtimestamp(ts,timezone.utc).date()
            if not (START<=d<=END): continue
            settlements=o.get('settledAmounts') or []
            for s in settlements:
                if not isinstance(s,dict): continue
                ti,to=norm(s.get('tokenIn')),norm(s.get('tokenOut'))
                ai,ao=s.get('amountIn'),s.get('amountOut')
                if {ti,to}!={BUIDL,USDC}: continue
                try: ai_i=int(ai); ao_i=int(ao)
                except Exception: continue
                if ai_i<=0 or ao_i<=0: continue
                if ti==BUIDL:
                    buidl=ai_i/1e6; usdc=ao_i/1e6
                else:
                    usdc=ai_i/1e6; buidl=ao_i/1e6
                if buidl<=0: continue
                valid.append({'fill_timestamp':ts,'day':d.isoformat(),'tx_hash':tx,'buidl':buidl,'usdc':usdc,'price_usdc_per_buidl':usdc/buidl})
    except Exception as exc:
        error=str(exc)
    days=defaultdict(list)
    for r in valid: days[r['day']].append(r)
    daily=[]
    for d,rs in sorted(days.items()):
        px=[r['price_usdc_per_buidl'] for r in sorted(rs,key=lambda x:x['fill_timestamp'])]
        daily.append({'day':d,'open':px[0],'high':max(px),'low':min(px),'close':px[-1],'trade_count':len(px),'volume_buidl':sum(r['buidl'] for r in rs)})
    have={x['day'] for x in daily}; missing=[]; cur=START
    while cur<=END:
        if cur.isoformat() not in have: missing.append(cur.isoformat())
        cur+=timedelta(days=1)
    if error: status='FAIL_CLOSED_SOURCE_OR_PARSE'
    elif not valid: status='FAIL_CLOSED_NO_PHYSICAL_FILLED_EXECUTIONS'
    elif missing: status='FAIL_CLOSED_FULL_CORPUS_QA'
    else: status='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION'
    summary={
      'schema_version':'GATE_BTC_2_V2A_BUIDL_UNISWAPX_QUALIFICATION_V1','symbol':'BUIDL','coin_id':'blackrock-usd-institutional-digital-liquidity-fund',
      'provider':'UNISWAPX_PUBLIC_ORDERS','pair':pair,'buidl_contract':BUIDL,'usdc_contract':USDC,'chain_id':CHAIN_ID,
      'requested_start_utc':START.isoformat(),'requested_end_utc':END.isoformat(),'query_url':url,
      'raw_sha256':sha(raw) if raw else None,'returned_orders':len(orders),'valid_pair_fills_in_window':len(valid),'daily_bucket_count':len(daily),
      'missing_days':missing,'status':status,'error':error,'source_admitted':False,'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,
      'qualification_only':True,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders_generated':0,'real_capital_brl':0,
      'no_retune':True,'no_backfill':True,'no_counter_reset':True,'fail_closed':True
    }
    (out/'FILLS.json').write_text(json.dumps(valid,indent=2,sort_keys=True)+'\n')
    (out/'DAILY_OHLCV.json').write_text(json.dumps(daily,indent=2,sort_keys=True)+'\n')
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,sort_keys=True))
    return 0

if __name__=='__main__': raise SystemExit(main())
