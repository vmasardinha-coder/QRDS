#!/usr/bin/env python3
"""Physical qualification for preregistered Kraken XMR/USD spot route.
Research/shadow only. No source admission, no D0, no credit.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

START=date(2026,8,4); END=date(2026,9,5); REQUIRED=33
PAIR="XMRUSD"; COIN_ID="monero"
KRAKEN="https://api.kraken.com/0/public"; UA="QRDS-GateBTC2-ResearchOnly/xmr-kraken-v1"

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def url(base:str, params:dict)->str:return base+"?"+urllib.parse.urlencode(params)
def req(u:str,retries:int=5)->bytes:
    last=None
    for n in range(retries):
        try:
            r=urllib.request.Request(u,headers={"Accept":"application/json","User-Agent":UA})
            with urllib.request.urlopen(r,timeout=60) as h:return h.read()
        except Exception as e:
            last=e
            if n+1<retries: time.sleep(min(30,2*(2**n)))
    raise RuntimeError(f"request failed after {retries} attempts url={u}: {type(last).__name__}: {last}")

def qa(rows):
    rows=sorted(rows,key=lambda x:x['day'])
    days=[x['day'] for x in rows]; have=set(days); miss=[]; d=START
    while d<=END:
        if d.isoformat() not in have: miss.append(d.isoformat())
        d+=timedelta(days=1)
    numeric=all(
        all(math.isfinite(float(x[k])) for k in ('open','high','low','close'))
        and float(x['low'])<=min(float(x['open']),float(x['close']))
        <=max(float(x['open']),float(x['close']))<=float(x['high'])
        for x in rows
    )
    ok=len(rows)==REQUIRED and len(days)==len(have) and not miss and numeric and days==sorted(days)
    return {'daily_bucket_count':len(rows),'missing_days':miss,'duplicate_days':len(days)-len(have),'monotonic_daily_dates':days==sorted(days),'finite_ohlc_and_invariant':numeric,'qa_pass':ok}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    result={
        'schema_version':'GATE_BTC_2_V2A_XMR_KRAKEN_EXACT_SOURCE_QUALIFICATION_V1',
        'symbol':'XMR','coin_id':COIN_ID,'provider':'KRAKEN_SPOT','pair':PAIR,
        'window_start_utc':START.isoformat(),'window_end_utc':END.isoformat(),'required_daily_buckets':REQUIRED,
        'qualification_only':True,'source_admitted':False,'complete_registry_claimed':False,'d0_started':False,
        'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,
        'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital_brl':0,
        'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True
    }
    try:
        cg_raw=req(url(f"https://api.coingecko.com/api/v3/coins/{COIN_ID}/tickers",{'exchange_ids':'kraken','order':'trust_score_desc','page':'1'}))
        cg=json.loads(cg_raw); tick=cg.get('tickers',[]) if isinstance(cg,dict) else []
        bridge=any(str((t.get('market') or {}).get('identifier','')).lower()=='kraken' and str(t.get('base','')).upper()=='XMR' and str(t.get('target','')).upper()=='USD' for t in tick)

        inst_raw=req(KRAKEN+'/AssetPairs'); inst_doc=json.loads(inst_raw)
        if inst_doc.get('error'): raise RuntimeError(f"kraken AssetPairs error: {inst_doc['error']}")
        pairs=inst_doc.get('result') or {}
        matches=[v for v in pairs.values() if isinstance(v,dict) and str(v.get('altname','')).upper()==PAIR]
        ident_ok=any(str(v.get('wsname','')).upper()=='XMR/USD' and str(v.get('base','')).upper() in ('XXMR','XMR') and str(v.get('quote','')).upper() in ('ZUSD','USD') for v in matches)

        start_s=int(datetime.combine(START,datetime.min.time(),tzinfo=timezone.utc).timestamp())
        ohlc_raw=req(url(KRAKEN+'/OHLC',{'pair':PAIR,'interval':1440,'since':start_s}))
        ohlc=json.loads(ohlc_raw)
        if ohlc.get('error'): raise RuntimeError(f"kraken OHLC error: {ohlc['error']}")
        body=ohlc.get('result') or {}; series=[]
        for k,v in body.items():
            if k!='last' and isinstance(v,list): series=v; break
        rows=[]
        for x in series:
            if not isinstance(x,list) or len(x)<5: continue
            ts=int(float(x[0])); day=datetime.fromtimestamp(ts,timezone.utc).date()
            if START<=day<=END:
                rows.append({'day':day.isoformat(),'open':float(x[1]),'high':float(x[2]),'low':float(x[3]),'close':float(x[4])})
        q=qa(rows)
        result.update({'coingecko_exact_market_bridge':bridge,'bridge_response_sha256':sha(cg_raw),'official_identity_ok':ident_ok,'instrument_response_sha256':sha(inst_raw),'ohlc_response_sha256':sha(ohlc_raw),**q})
        result['status']='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION' if bridge and ident_ok and q['qa_pass'] else 'FAIL_CLOSED_FULL_CORPUS_OR_IDENTITY_QA'
    except Exception as e:
        result.update({'qa_pass':False,'status':'FAIL_CLOSED_SOURCE_OR_PARSE','error':f'{type(e).__name__}: {e}'})
    (a.out/'RESULTS.json').write_text(json.dumps([result],indent=2,sort_keys=True)+'\n',encoding='utf-8')
    summary={k:result.get(k) for k in ('schema_version','symbol','provider','pair','status','error','qa_pass','daily_bucket_count','missing_days','coingecko_exact_market_bridge','official_identity_ok','qualification_only','source_admitted','complete_registry_claimed','d0_started','historical_credit','scientific_credit','prospective_credit','d0_credit','research_only','shadow_only','not_approved','engine_feed','orders','real_capital_brl','no_retune','no_backfill','no_counter_reset','no_silent_source_substitution','fail_closed')}
    (a.out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(summary,sort_keys=True))

if __name__=='__main__': main()
