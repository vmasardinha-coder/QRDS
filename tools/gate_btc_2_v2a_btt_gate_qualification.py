#!/usr/bin/env python3
"""Physical qualification for preregistered BTT/USDT Gate spot route.
Reads frozen BTT coin identity from canonical #608 parent evidence.
Research/shadow only. No source admission, no D0, no credit.
"""
from __future__ import annotations
import argparse, hashlib, json, math, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

START=date(2026,8,4); END=date(2026,9,5); REQUIRED=33
PAIR='BTT_USDT'; GATE='https://api.gateio.ws/api/v4'; UA='QRDS-GateBTC2-ResearchOnly/btt-gate-v1'

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def url(base:str, params:dict)->str:return base+'?'+urllib.parse.urlencode(params)
def req(u:str,retries:int=5)->bytes:
    last=None
    for n in range(retries):
        try:
            r=urllib.request.Request(u,headers={'Accept':'application/json','User-Agent':UA})
            with urllib.request.urlopen(r,timeout=60) as h:return h.read()
        except Exception as e:
            last=e
            if n+1<retries: time.sleep(min(30,2*(2**n)))
    raise RuntimeError(f'request failed after {retries} attempts url={u}: {type(last).__name__}: {last}')

def load_parent_coin_id(path:Path)->str:
    d=json.load(open(path,encoding='utf-8'))
    rows=d if isinstance(d,list) else d.get('results',d.get('symbols',[]))
    if not isinstance(rows,list): raise RuntimeError('parent RESULTS has no list payload')
    hits=[r for r in rows if isinstance(r,dict) and str(r.get('symbol','')).upper()=='BTT']
    if len(hits)!=1: raise RuntimeError(f'expected exactly one BTT parent row, got {len(hits)}')
    row=hits[0]
    cid=row.get('coin_id') or row.get('coingecko_coin_id') or row.get('frozen_coin_id')
    if not cid: raise RuntimeError('BTT parent row lacks frozen CoinGecko coin identity')
    return str(cid)

def qa(rows):
    rows=sorted(rows,key=lambda x:x['day']); days=[x['day'] for x in rows]; have=set(days)
    miss=[]; d=START
    while d<=END:
        if d.isoformat() not in have: miss.append(d.isoformat())
        d+=timedelta(days=1)
    finite=True
    for x in rows:
        try:
            o,h,l,c=[float(x[k]) for k in ('open','high','low','close')]
            finite=finite and all(math.isfinite(v) for v in (o,h,l,c)) and l<=min(o,c)<=max(o,c)<=h
        except Exception: finite=False
    ok=len(rows)==REQUIRED and len(days)==len(have) and not miss and days==sorted(days) and finite
    return {'daily_bucket_count':len(rows),'missing_days':miss,'duplicate_days':len(days)-len(have),'monotonic_daily_dates':days==sorted(days),'finite_ohlc_and_invariant':finite,'qa_pass':ok}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--parent-results',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    cid=load_parent_coin_id(a.parent_results)
    result={'schema_version':'GATE_BTC_2_V2A_BTT_GATE_EXACT_SOURCE_QUALIFICATION_V1','symbol':'BTT','coin_id':cid,'provider':'GATE_SPOT','pair':PAIR,'window_start_utc':START.isoformat(),'window_end_utc':END.isoformat(),'required_daily_buckets':REQUIRED,'qualification_only':True,'source_admitted':False,'complete_registry_claimed':False,'d0_started':False,'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True}
    try:
        cg_raw=req(url(f'https://api.coingecko.com/api/v3/coins/{cid}/tickers',{'exchange_ids':'gate','order':'trust_score_desc','page':'1'}))
        cg=json.loads(cg_raw); ticks=cg.get('tickers',[]) if isinstance(cg,dict) else []
        bridge=any(str((t.get('market') or {}).get('identifier','')).lower()=='gate' and str(t.get('base','')).upper()=='BTT' and str(t.get('target','')).upper()=='USDT' for t in ticks)
        inst_raw=req(GATE+'/spot/currency_pairs/'+PAIR); inst=json.loads(inst_raw)
        ident_ok=isinstance(inst,dict) and str(inst.get('id','')).upper()==PAIR and str(inst.get('base','')).upper()=='BTT' and str(inst.get('quote','')).upper()=='USDT'
        start_s=int(datetime.combine(START,datetime.min.time(),tzinfo=timezone.utc).timestamp())
        end_s=int(datetime.combine(END+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1
        candle_raw=req(url(GATE+'/spot/candlesticks',{'currency_pair':PAIR,'interval':'1d','from':start_s,'to':end_s}))
        arr=json.loads(candle_raw); rows=[]
        if isinstance(arr,list):
            for x in arr:
                if not isinstance(x,list) or len(x)<6: continue
                rows.append({'day':datetime.fromtimestamp(int(float(x[0])),timezone.utc).date().isoformat(),'open':float(x[5]),'high':float(x[3]),'low':float(x[4]),'close':float(x[2])})
        q=qa(rows)
        result.update({'coingecko_exact_market_bridge':bridge,'bridge_response_sha256':sha(cg_raw),'official_identity_ok':ident_ok,'instrument_response_sha256':sha(inst_raw),'candle_response_sha256':sha(candle_raw),**q})
        result['status']='QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION' if bridge and ident_ok and q['qa_pass'] else 'FAIL_CLOSED_FULL_CORPUS_OR_IDENTITY_QA'
    except Exception as e:
        result.update({'qa_pass':False,'status':'FAIL_CLOSED_SOURCE_OR_PARSE','error':f'{type(e).__name__}: {e}'})
    (a.out/'RESULTS.json').write_text(json.dumps([result],indent=2,sort_keys=True)+'\n',encoding='utf-8')
    summary={k:result.get(k) for k in ('schema_version','symbol','coin_id','provider','pair','status','error','qa_pass','daily_bucket_count','missing_days','coingecko_exact_market_bridge','official_identity_ok','qualification_only','source_admitted','complete_registry_claimed','d0_started','historical_credit','scientific_credit','prospective_credit','d0_credit','research_only','shadow_only','not_approved','engine_feed','orders','real_capital_brl','no_retune','no_backfill','no_counter_reset','no_silent_source_substitution','fail_closed')}
    (a.out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(summary,sort_keys=True))

if __name__=='__main__': main()
