#!/usr/bin/env python3
import csv, hashlib, json, os, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

EXCHANGE_INFO='https://fapi.binance.com/fapi/v1/exchangeInfo'
TICKER_24H='https://fapi.binance.com/fapi/v1/ticker/24hr'
EXCLUDED={'USDT','USDC','FDUSD','TUSD','USDP','DAI','BUSD','EUR','BRL','TRY','JPY','GBP','AUD'}
STRATA=(30,50,75)

def fetch(url):
    req=urllib.request.Request(url, headers={'User-Agent':'QRDS-GATE-BTC-Research/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def write_csv(path, rows):
    fields=['liquidity_rank','symbol','baseAsset','quoteAsset','contractType','status','quoteVolume24h','lastPrice','priceChangePercent']
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main():
    out=Path(os.environ.get('DELTA_V12_UNIVERSE_OUT','delta_v12_universe_snapshot'))
    out.mkdir(parents=True,exist_ok=True)
    ex_raw=fetch(EXCHANGE_INFO); tk_raw=fetch(TICKER_24H)
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
    now=datetime.now(timezone.utc).isoformat()
    manifest={
      'version':'DELTA_V12_UNIVERSE_SNAPSHOT_1.0',
      'captured_at_utc':now,
      'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0,
      'source':{'exchange_info':EXCHANGE_INFO,'ticker_24h':TICKER_24H},
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

if __name__=='__main__': main()
