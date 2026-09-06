#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered USTB/USDC Multiliquid route."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RPC='https://api.mainnet-beta.solana.com'
PAIR='CPCnfrQwHEoDDt9BYCw5ZygUfjtuGK5tVRhdgzNUdWYH'
PROGRAM='FKeT8H2RSgsamrABNNxwT5f9g3n9msfm6D5AvocjrJAD'
USTB='CCz3SGVziFeLYk2xfEstkiqJfYkjaSWb2GCABYsVcjo2'
USDC='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
END=date(2026,9,5); START=END-timedelta(days=32)
UA='QRDS-GateBTC2-ResearchOnly/1'

def rpc(method,params,retries=5):
    body=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params},separators=(',',':')).encode()
    last=None
    for n in range(retries):
        try:
            req=urllib.request.Request(RPC,data=body,headers={'Content-Type':'application/json','User-Agent':UA})
            with urllib.request.urlopen(req,timeout=90) as r: raw=r.read()
            obj=json.loads(raw)
            if obj.get('error'): raise RuntimeError('RPC_ERROR:'+json.dumps(obj['error'],sort_keys=True))
            return raw,obj.get('result')
        except Exception as exc:
            last=exc; time.sleep(min(8,2**n))
    raise RuntimeError(f'RPC_FAILED:{last}')

def acct_keys(tx):
    msg=((tx or {}).get('transaction') or {}).get('message') or {}
    out=[]
    for x in msg.get('accountKeys') or []:
        out.append(str(x.get('pubkey')) if isinstance(x,dict) else str(x))
    meta=(tx or {}).get('meta') or {}
    loaded=meta.get('loadedAddresses') or {}
    out += [str(x) for x in (loaded.get('writable') or [])+(loaded.get('readonly') or [])]
    return out

def token_map(rows):
    out={}
    for x in rows or []:
        try:
            idx=int(x['accountIndex']); mint=str(x['mint']); owner=str(x.get('owner') or '')
            ui=x.get('uiTokenAmount') or {}; raw=int(ui.get('amount') or 0); dec=int(ui.get('decimals') or 0)
            out[(idx,mint,owner)]=(raw,dec)
        except Exception: continue
    return out

def extract_trade(sig,tx):
    if not tx or tx.get('blockTime') is None: return None
    ts=int(tx['blockTime']); day=datetime.fromtimestamp(ts,timezone.utc).date()
    if not (START<=day<=END): return None
    keys=acct_keys(tx)
    if PAIR not in keys or PROGRAM not in keys: return None
    meta=tx.get('meta') or {}
    if meta.get('err') is not None: return None
    pre=token_map(meta.get('preTokenBalances')); post=token_map(meta.get('postTokenBalances'))
    candidates=[]
    common=set(pre)|set(post)
    by_owner=defaultdict(dict)
    for key in common:
        idx,mint,owner=key
        if mint not in (USTB,USDC) or not owner: continue
        a,dec=pre.get(key,(0,post.get(key,(0,0))[1])); b,dec2=post.get(key,(0,dec))
        dec=max(dec,dec2); delta=(b-a)/(10**dec if dec>=0 else 1)
        if abs(delta)>0: by_owner[owner][mint]=by_owner[owner].get(mint,0.0)+delta
    for owner,d in by_owner.items():
        du=float(d.get(USTB,0)); dc=float(d.get(USDC,0))
        if du==0 or dc==0 or du*dc>=0: continue
        qty=abs(du); usd=abs(dc)
        if qty>0 and usd>0: candidates.append((owner,qty,usd,usd/qty))
    if not candidates: return None
    candidates.sort(key=lambda x:(-(x[1]*x[2]),x[0]))
    owner,qty,usd,px=candidates[0]
    if not (0.01 <= px <= 1000): return None
    return {'signature':sig,'timestamp':ts,'day':day.isoformat(),'owner':owner,'ustb_amount':qty,'usdc_amount':usd,'price_usdc_per_ustb':px}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args()
    out=a.output_dir; out.mkdir(parents=True,exist_ok=True)
    sigs=[]; before=None; pages=[]; history_complete=False; error=None
    try:
        for page in range(8):
            cfg={'limit':1000}
            if before: cfg['before']=before
            raw,res=rpc('getSignaturesForAddress',[PAIR,cfg]); pages.append({'sha256':hashlib.sha256(raw).hexdigest(),'count':len(res or [])})
            rows=res or []; sigs.extend(rows)
            if not rows: history_complete=True; break
            oldest=min((x.get('blockTime') for x in rows if x.get('blockTime') is not None),default=None)
            if oldest is not None and datetime.fromtimestamp(int(oldest),timezone.utc).date()<START:
                history_complete=True; break
            before=str(rows[-1]['signature'])
        if not history_complete: raise RuntimeError('SIGNATURE_HISTORY_TRUNCATED_BEFORE_FROZEN_START_NOT_PROVEN')
        (out/'SIGNATURES.json').write_text(json.dumps(sigs,indent=2,sort_keys=True)+'\n')
        trades=[]; tx_hashes=[]; seen=set()
        for row in sigs:
            bt=row.get('blockTime'); sig=str(row.get('signature') or '')
            if not sig or bt is None: continue
            d=datetime.fromtimestamp(int(bt),timezone.utc).date()
            if d<START or d>END or sig in seen: continue
            seen.add(sig)
            raw,tx=rpc('getTransaction',[sig,{'encoding':'jsonParsed','maxSupportedTransactionVersion':0}])
            tx_hashes.append({'signature':sig,'sha256':hashlib.sha256(raw).hexdigest()})
            t=extract_trade(sig,tx)
            if t: trades.append(t)
            time.sleep(0.12)
        trades.sort(key=lambda x:x['timestamp'])
        (out/'TRADES.json').write_text(json.dumps(trades,indent=2,sort_keys=True)+'\n')
        days=defaultdict(list)
        for t in trades: days[t['day']].append(t)
        daily=[]
        for d,rs in sorted(days.items()):
            rs=sorted(rs,key=lambda x:x['timestamp']); px=[x['price_usdc_per_ustb'] for x in rs]
            daily.append({'day':d,'open':px[0],'high':max(px),'low':min(px),'close':px[-1],'volume_ustb':sum(x['ustb_amount'] for x in rs),'trade_count':len(rs)})
        (out/'DAILY_OHLCV.json').write_text(json.dumps(daily,indent=2,sort_keys=True)+'\n')
        have={x['day'] for x in daily}; missing=[]; cur=START
        while cur<=END:
            if cur.isoformat() not in have: missing.append(cur.isoformat())
            cur+=timedelta(days=1)
        qa=bool(trades) and len(daily)==33 and not missing and all(x['low']<=min(x['open'],x['close'])<=max(x['open'],x['close'])<=x['high'] and x['volume_ustb']>=0 for x in daily)
        status='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION' if qa else ('FAIL_CLOSED_NO_PHYSICAL_SWAPS' if not trades else 'FAIL_CLOSED_FULL_CORPUS_QA')
    except Exception as exc:
        error=str(exc); trades=[]; daily=[]; missing=[]; tx_hashes=[]; status='FAIL_CLOSED_SOURCE_OR_PARSE'; qa=False
    summary={'schema_version':'GATE_BTC_2_V2A_USTB_MULTILIQUID_QUALIFICATION_V1','symbol':'USTB','coin_id':'superstate-short-duration-us-government-securities-fund-ustb','provider':'MULTILIQUID_SOLANA_MAINNET','pair_pda':PAIR,'swap_program':PROGRAM,'ustb_mint':USTB,'usdc_mint':USDC,'requested_start_utc':START.isoformat(),'requested_end_utc':END.isoformat(),'signature_pages':pages,'signature_count':len(sigs),'history_complete_to_before_start':history_complete,'transaction_hashes':tx_hashes,'physical_trade_count':len(trades),'daily_bucket_count':len(daily),'missing_days':missing,'qa_pass':qa,'status':status,'error':error,'source_admitted':False,'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'qualification_only':True,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders_generated':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
