#!/usr/bin/env python3
import csv, hashlib, json, os, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URLS=(
    'https://fapi.binance.com',
    'https://fapi1.binance.com',
    'https://fapi2.binance.com',
    'https://fapi3.binance.com',
    'https://fapi4.binance.com',
)
EXCHANGE_INFO_PATH='/fapi/v1/exchangeInfo'
TICKER_24H_PATH='/fapi/v1/ticker/24hr'
EXCLUDED={'USDT','USDC','FDUSD','TUSD','USDP','DAI','BUSD','EUR','BRL','TRY','JPY','GBP','AUD'}
STRATA=(30,50,75)

def fetch_url(url):
    req=urllib.request.Request(url, headers={'User-Agent':'QRDS-GATE-BTC-Research/1.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def configured_base_urls():
    raw=os.environ.get('DELTA_V12_BINANCE_BASE_URLS','')
    if not raw.strip(): return DEFAULT_BASE_URLS
    return tuple(x.strip().rstrip('/') for x in raw.split(',') if x.strip())

def fetch_path(path, base_urls=None, attempts_per_base=2):
    errors=[]
    for base in base_urls or configured_base_urls():
        url=f'{base}{path}'
        for attempt in range(1,attempts_per_base+1):
            try:
                return fetch_url(url), url, errors
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
                errors.append({'url':url,'attempt':attempt,'type':type(exc).__name__,'message':str(exc)})
                if attempt < attempts_per_base: time.sleep(attempt)
    raise RuntimeError(json.dumps({'path':path,'attempts':errors},sort_keys=True))

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def write_csv(path, rows):
    fields=['liquidity_rank','symbol','baseAsset','quoteAsset','contractType','status','quoteVolume24h','lastPrice','priceChangePercent']
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    out=Path(os.environ.get('DELTA_V12_UNIVERSE_OUT','delta_v12_universe_snapshot'))
    out.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    try:
        ex_raw, ex_url, ex_errors=fetch_path(EXCHANGE_INFO_PATH)
        tk_raw, tk_url, tk_errors=fetch_path(TICKER_24H_PATH)
    except Exception as exc:
        failure={
          'version':'DELTA_V12_UNIVERSE_SNAPSHOT_FAILURE_1.0',
          'captured_at_utc':now,
          'status':'FAIL_SOURCE_UNAVAILABLE',
          'error_type':type(exc).__name__,
          'error':str(exc),
          'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,
          'orders':0,'real_capital':0,'promotion_eligible':False,
          'synthetic_or_backfilled_data_used':False,
        }
        (out/'UNIVERSE_FAILURE.json').write_text(json.dumps(failure,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(failure,sort_keys=True),file=sys.stderr)
        return 1
    (out/'RAW_EXCHANGE_INFO.json').write_bytes(ex_raw)
    (out/'RAW_TICKER_24H.json').write_bytes(tk_raw)
    ex=json.loads(ex_raw); tick=json.loads(tk_raw)
    tick_by_symbol={x.get('symbol'):x for x in tick if isinstance(x,dict) and x.get('symbol')}
    rows=[]
    for s in ex.get('symbols',[]):
        if s.get('status')!='TRADING': continue
        if s.get('contractType')!='PERPETUAL': continue
        if s.get('quoteAsset')!='USDT': continue
        if s.get('baseAsset') in EXCLUDED: continue
        t=tick_by_symbol.get(s.get('symbol'),{})
        try: qv=float(t.get('quoteVolume') or 0)
        except Exception: qv=0.0
        if not (qv>0): continue
        rows.append({
            'liquidity_rank':0,
            'symbol':s.get('symbol'),
            'baseAsset':s.get('baseAsset'),
            'quoteAsset':s.get('quoteAsset'),
            'contractType':s.get('contractType'),
            'status':s.get('status'),
            'quoteVolume24h':qv,
            'lastPrice':t.get('lastPrice',''),
            'priceChangePercent':t.get('priceChangePercent','')
        })
    rows.sort(key=lambda x:x['quoteVolume24h'],reverse=True)
    for i,r in enumerate(rows,1): r['liquidity_rank']=i
    write_csv(out/'UNIVERSE_ALL.csv',rows)
    for n in STRATA: write_csv(out/f'UNIVERSE_TOP{n}.csv',rows[:n])
    manifest={
      'version':'DELTA_V12_UNIVERSE_SNAPSHOT_1.0',
      'captured_at_utc':now,
      'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0,
      'source':{'exchange_info':ex_url,'ticker_24h':tk_url},
      'source_attempt_errors':{'exchange_info':ex_errors,'ticker_24h':tk_errors},
      'raw_sha256':{'exchange_info':sha256(ex_raw),'ticker_24h':sha256(tk_raw)},
      'eligible_count':len(rows),'liquidity_strata':list(STRATA),
      'ranking':'descending 24h quoteVolume at snapshot time',
      'external_holdings_used_for_selection':False,
      'historical_replay_before_freeze':'DIAGNOSTIC_ONLY',
      'clean_evidence':'PROSPECTIVE_FROM_FREEZE'
    }
    (out/'UNIVERSE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'status':'PASS_RESEARCH_UNIVERSE_SNAPSHOT','eligible_count':len(rows),'captured_at_utc':now,'orders':0,'real_capital':0}))
    if len(rows)<30: raise SystemExit('FAIL_CLOSED: fewer than 30 eligible contracts')
    return 0

if __name__=='__main__': raise SystemExit(main())
