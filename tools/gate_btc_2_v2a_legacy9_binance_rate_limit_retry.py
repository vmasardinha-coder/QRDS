#!/usr/bin/env python3
"""Bounded mechanical retry for nine #607 Binance qualifications blocked only by CoinGecko HTTP 429.
Same frozen provider/pair/window as #606/#607; no new route and zero credit.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TARGETS=set("AVAX BTT DCR FIL JST POL SUN UNI XRP".split())
START=date(2026,8,4); END=date(2026,9,5); REQUIRED=33
BINANCE="https://data-api.binance.vision"; UA="QRDS-GateBTC2-ResearchOnly/legacy9-retry-v1"
def sha(x:bytes)->str:return hashlib.sha256(x).hexdigest()
def url(b,p):return b+"?"+urllib.parse.urlencode(p)
def req(u,retries=8):
    last=None
    for n in range(retries):
        try:
            r=urllib.request.Request(u,headers={"Accept":"application/json","User-Agent":UA})
            with urllib.request.urlopen(r,timeout=60) as h:return h.read()
        except Exception as e:
            last=e; time.sleep(min(60,5*(n+1)))
    raise RuntimeError(f"request failed: {type(last).__name__}: {last}")
def qa(rows):
    days=[x['day'] for x in rows]; have=set(days); miss=[]; d=START
    while d<=END:
        if d.isoformat() not in have:miss.append(d.isoformat())
        d+=timedelta(days=1)
    numeric=all(all(math.isfinite(float(x[k])) for k in ('open','high','low','close')) and float(x['low'])<=min(float(x['open']),float(x['close']))<=max(float(x['open']),float(x['close']))<=float(x['high']) for x in rows)
    ok=len(rows)==REQUIRED and len(days)==len(have) and not miss and days==sorted(days) and numeric
    return {'daily_bucket_count':len(rows),'missing_days':miss,'duplicate_days':len(days)-len(have),'monotonic_daily_dates':days==sorted(days),'finite_ohlc_and_invariant':numeric,'qa_pass':ok}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--parent-results',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    parent=json.loads(a.parent_results.read_text(encoding='utf-8')); by={x['symbol']:x for x in parent if x.get('symbol') in TARGETS}
    if set(by)!=TARGETS:raise RuntimeError('target-set mismatch')
    exraw=req(BINANCE+'/api/v3/exchangeInfo'); exhash=sha(exraw); ex={x.get('symbol'):x for x in json.loads(exraw).get('symbols',[])}
    sm=int(datetime.combine(START,datetime.min.time(),tzinfo=timezone.utc).timestamp()*1000); em=int(datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp()*1000)-1
    results=[]
    for i,s in enumerate(sorted(TARGETS),1):
        p=by[s]; cid=p['coin_id']; pair=s+'USDT'; print(f'RETRY {i}/9 {pair}',flush=True)
        r={'symbol':s,'coin_id':cid,'provider':'BINANCE_SPOT','pair':pair,'retry_reason':'PARENT_HTTP_429_ONLY','qualification':'QUALIFICATION_ONLY','source_admitted':False,'scientific_credit':False,'prospective_credit':False,'d0_credit':0}
        try:
            craw=req(url(f"https://api.coingecko.com/api/v3/coins/{urllib.parse.quote(cid,safe='')}/tickers",{'exchange_ids':'binance','order':'trust_score_desc','page':'1'})); co=json.loads(craw); tick=co.get('tickers',[]) if isinstance(co,dict) else []
            bridge=any(str((t.get('market') or {}).get('identifier','')).lower()=='binance' and str(t.get('base','')).upper()==s and str(t.get('target','')).upper()=='USDT' for t in tick)
            ident=ex.get(pair) or {}; ident_ok=ident.get('baseAsset')==s and ident.get('quoteAsset')=='USDT'
            kraw=req(url(BINANCE+'/api/v3/klines',{'symbol':pair,'interval':'1d','startTime':sm,'endTime':em,'limit':1000})); arr=json.loads(kraw)
            rows=[{'day':datetime.fromtimestamp(int(x[0])/1000,timezone.utc).date().isoformat(),'open':float(x[1]),'high':float(x[2]),'low':float(x[3]),'close':float(x[4])} for x in arr]; q=qa(rows)
            r.update({'coingecko_exact_market_bridge':bridge,'bridge_response_sha256':sha(craw),'official_identity_ok':ident_ok,'exchange_info_sha256':exhash,'candle_response_sha256':sha(kraw),**q}); r['status']='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION' if bridge and ident_ok and q['qa_pass'] else 'FAIL_CLOSED_FULL_CORPUS_OR_IDENTITY_QA'
        except Exception as e:r.update({'qa_pass':False,'status':'FAIL_CLOSED_SOURCE_OR_PARSE','error':f'{type(e).__name__}: {e}'})
        results.append(r); time.sleep(10)
    failed=[x['symbol'] for x in results if x['status']!='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION']
    summary={'schema_version':'GATE_BTC_2_V2A_LEGACY9_BINANCE_RATE_LIMIT_RETRY_V1','parent_pr':607,'prereg_pr':606,'target_symbol_count':9,'passed_symbol_count':9-len(failed),'failed_symbol_count':len(failed),'failed_symbols':failed,'all_9_pass':not failed,'results':results,'qualification_only':True,'source_admission_changed':False,'complete_registry_claimed':False,'d0_started':False,'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'fail_closed':True}
    (a.out/'RESULTS.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n');(a.out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps({k:summary[k] for k in ('passed_symbol_count','failed_symbol_count','failed_symbols','all_9_pass')},sort_keys=True))
if __name__=='__main__':main()
