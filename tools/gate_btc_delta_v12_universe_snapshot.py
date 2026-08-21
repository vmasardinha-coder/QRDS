#!/usr/bin/env python3
import csv, hashlib, io, json, os, sys, time, urllib.error, urllib.request, zipfile
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
STRATA=(30,50,75,100)

def fetch_url(url):
    req=urllib.request.Request(url, headers={'User-Agent':'QRDS-GATE-BTC-Research/1.0'})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read()

def configured_base_urls():
    raw=os.environ.get('DELTA_V12_BINANCE_BASE_URLS','')
    if not raw.strip(): return DEFAULT_BASE_URLS
    return tuple(x.strip().rstrip('/') for x in raw.split(',') if x.strip())

def fetch_path(path, base_urls=None, attempts_per_base=2, json_root_type=None):
    errors=[]
    for base in base_urls or configured_base_urls():
        url=f'{base}{path}'
        for attempt in range(1,attempts_per_base+1):
            try:
                body=fetch_url(url)
                if not body: raise ValueError('empty response body')
                parsed=None
                if json_root_type is not None:
                    parsed=json.loads(body)
                    if not isinstance(parsed,json_root_type):
                        raise ValueError(f'unexpected JSON root: {type(parsed).__name__}')
                return body, url, errors, parsed
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                errors.append({'url':url,'attempt':attempt,'type':type(exc).__name__,'message':str(exc)})
                if attempt < attempts_per_base: time.sleep(attempt)
    raise RuntimeError(json.dumps({'path':path,'attempts':errors},sort_keys=True))

def sha256(b):
    return hashlib.sha256(b).hexdigest()

def write_csv(path, rows):
    fields=['liquidity_rank','symbol','baseAsset','quoteAsset','contractType','status','quoteVolume24h','lastPrice','priceChangePercent','sourceVenue','liquiditySource']
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def truthy(value):
    return str(value).strip().lower() in {'1','true','yes','y'}

def number(value):
    try: return float(value or 0)
    except (TypeError,ValueError): return 0.0

def load_gateway_artifact(path):
    outer_raw=Path(path).read_bytes()
    with zipfile.ZipFile(io.BytesIO(outer_raw)) as outer:
        nested_name='gateway_daily/linux_public_capture_outputs.zip'
        nested_raw=outer.read(nested_name)
    with zipfile.ZipFile(io.BytesIO(nested_raw)) as nested:
        status_name='outputs/scanner_snapshot_status.json'
        csv_name='outputs/scanner_top500_raw.csv'
        status_raw=nested.read(status_name)
        csv_raw=nested.read(csv_name)
    status=json.loads(status_raw)
    if status.get('critical_failed_checks'):
        raise RuntimeError(f"gateway snapshot has critical failures: {status['critical_failed_checks']}")
    if status.get('snapshot_status') not in {'SNAPSHOT_USABLE','SNAPSHOT_USABLE_WITH_DATA_WARNINGS'}:
        raise RuntimeError(f"gateway snapshot not usable: {status.get('snapshot_status')}")
    source_rows=list(csv.DictReader(io.StringIO(csv_raw.decode('utf-8-sig'))))
    if not source_rows:
        raise RuntimeError('gateway scanner universe is empty')
    return outer_raw,nested_raw,status_raw,csv_raw,status,source_rows

def gateway_rows(source_rows):
    rows=[]
    liquidity_fields=(
        ('binance_futures_quote_volume','BINANCE_FUTURES'),
        ('bybit_turnover24h','BYBIT'),
        ('hyperliquid_day_ntl_vlm','HYPERLIQUID'),
        ('binance_quote_volume','BINANCE_SPOT_PROXY'),
        ('okx_volume','OKX_PROXY'),
        ('cg_volume','COINGECKO_PROXY'),
    )
    for source in source_rows:
        base=(source.get('base') or '').strip().upper()
        if not base or base in EXCLUDED or not truthy(source.get('short_available')): continue
        candidates=[(number(source.get(field)),venue,field) for field,venue in liquidity_fields]
        qv,venue,liquidity_source=max(candidates,key=lambda item:item[0])
        if not (qv>0): continue
        if truthy(source.get('binance_futures_available')) and source.get('binance_futures_symbol'):
            symbol=source['binance_futures_symbol']; venue_symbol='BINANCE_FUTURES'
        elif truthy(source.get('bybit_linear_available')) and source.get('bybit_symbol'):
            symbol=source['bybit_symbol']; venue_symbol='BYBIT'
        elif truthy(source.get('okx_swap_available')):
            symbol=f'{base}-USDT-SWAP'; venue_symbol='OKX_SWAP'
        elif truthy(source.get('hyperliquid_perp_available')):
            symbol=base; venue_symbol='HYPERLIQUID'
        else:
            symbol=base; venue_symbol=venue
        last_price=(source.get('binance_futures_last') or source.get('bybit_last') or
                    source.get('okx_last') or source.get('binance_last') or '')
        rows.append({
            'liquidity_rank':0,'symbol':symbol,'baseAsset':base,'quoteAsset':'USDT',
            'contractType':'MULTI_VENUE_SHORTABLE','status':'ELIGIBLE',
            'quoteVolume24h':qv,'lastPrice':last_price,'priceChangePercent':'',
            'sourceVenue':venue_symbol,'liquiditySource':liquidity_source,
        })
    rows.sort(key=lambda x:(-x['quoteVolume24h'],x['baseAsset']))
    for i,row in enumerate(rows,1): row['liquidity_rank']=i
    return rows

def write_gateway_snapshot(out, now, artifact_path):
    outer_raw,nested_raw,status_raw,csv_raw,status,source_rows=load_gateway_artifact(artifact_path)
    (out/'RAW_GATEWAY_SCANNER_TOP500.csv').write_bytes(csv_raw)
    (out/'RAW_GATEWAY_STATUS.json').write_bytes(status_raw)
    rows=gateway_rows(source_rows)
    write_csv(out/'UNIVERSE_ALL.csv',rows)
    for n in STRATA: write_csv(out/f'UNIVERSE_TOP{n}.csv',rows[:n])
    manifest={
      'version':'DELTA_V12_UNIVERSE_SNAPSHOT_2.0',
      'captured_at_utc':now,
      'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0,
      'source':{
        'type':'IMMUTABLE_GATE_BTC_DAILY_RESEARCH_ARTIFACT',
        'workflow_run_id':os.environ.get('SOURCE_RUN_ID',''),
        'artifact_id':os.environ.get('SOURCE_ARTIFACT_ID',''),
        'outer_path':str(artifact_path),
        'nested_path':'gateway_daily/linux_public_capture_outputs.zip',
        'scanner_path':'outputs/scanner_top500_raw.csv',
      },
      'raw_sha256':{
        'daily_artifact_zip':sha256(outer_raw),'gateway_outputs_zip':sha256(nested_raw),
        'scanner_top500_raw':sha256(csv_raw),'scanner_snapshot_status':sha256(status_raw),
      },
      'gateway_snapshot_status':status.get('snapshot_status'),
      'gateway_warning_failed_checks':status.get('warning_failed_checks',[]),
      'gateway_critical_failed_checks':status.get('critical_failed_checks',[]),
      'eligible_count':len(rows),'liquidity_strata':list(STRATA),
      'ranking':'descending max observed 24h liquidity across eligible Gateway venues; spot/CG volume is a documented proxy only when derivative venue volume is unavailable',
      'external_holdings_used_for_selection':False,
      'historical_replay_before_freeze':'DIAGNOSTIC_ONLY',
      'clean_evidence':'PROSPECTIVE_FROM_IMMUTABLE_DAILY_ARTIFACT',
      'synthetic_or_backfilled_data_used':False,
    }
    (out/'UNIVERSE_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'status':'PASS_RESEARCH_UNIVERSE_SNAPSHOT','eligible_count':len(rows),'captured_at_utc':now,'orders':0,'real_capital':0}))
    if len(rows)<30: raise SystemExit('FAIL_CLOSED: fewer than 30 eligible contracts')
    return 0

def main():
    out=Path(os.environ.get('DELTA_V12_UNIVERSE_OUT','delta_v12_universe_snapshot'))
    out.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    artifact_path=os.environ.get('DELTA_V12_DAILY_ARTIFACT','').strip()
    if artifact_path:
        try:
            return write_gateway_snapshot(out,now,artifact_path)
        except Exception as exc:
            failure={
              'version':'DELTA_V12_UNIVERSE_SNAPSHOT_FAILURE_2.0','captured_at_utc':now,
              'status':'FAIL_IMMUTABLE_GATEWAY_ARTIFACT','error_type':type(exc).__name__,'error':str(exc),
              'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,
              'orders':0,'real_capital':0,'promotion_eligible':False,
              'synthetic_or_backfilled_data_used':False,
            }
            (out/'UNIVERSE_FAILURE.json').write_text(json.dumps(failure,indent=2,sort_keys=True),encoding='utf-8')
            print(json.dumps(failure,sort_keys=True),file=sys.stderr)
            return 1
    try:
        ex_raw, ex_url, ex_errors, ex=fetch_path(EXCHANGE_INFO_PATH,json_root_type=dict)
        tk_raw, tk_url, tk_errors, tick=fetch_path(TICKER_24H_PATH,json_root_type=list)
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
            'priceChangePercent':t.get('priceChangePercent',''),
            'sourceVenue':'BINANCE_FUTURES','liquiditySource':'quoteVolume',
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
