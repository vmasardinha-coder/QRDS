#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered OSL USDGO/USD source."""
from __future__ import annotations
import argparse, hashlib, json, urllib.error, urllib.request
from pathlib import Path

PAIR='USDGOUSD'
INSTRUMENT_URL='https://trade-hk.osl.com/api/v4/instrument'
TX_URL='https://trade-hk.osl.com/api/3/transaction/list'
DOC_URLS=[
 'https://osl.com/reference/api-summary',
 'https://osl.com/reference/introduction',
 'https://osl.com/reference/get-transactions',
 'https://www.osl.com/en/announcement/new-listing-on-osl-usdgo-usdgo',
]
UA='QRDS-GateBTC2-ResearchOnly/1'

def req(url, method='GET', body=None):
    data=None if body is None else json.dumps(body,separators=(',',':')).encode()
    r=urllib.request.Request(url,data=data,method=method,headers={'User-Agent':UA,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(r,timeout=45) as h:
            raw=h.read(); return {'url':url,'http_status':h.status,'sha256':hashlib.sha256(raw).hexdigest(),'body':raw.decode('utf-8','replace')}
    except urllib.error.HTTPError as e:
        raw=e.read(); return {'url':url,'http_status':e.code,'sha256':hashlib.sha256(raw).hexdigest(),'body':raw.decode('utf-8','replace')}
    except Exception as e:
        return {'url':url,'error':f'{type(e).__name__}:{e}'}

def find_pair(obj):
    if isinstance(obj,dict):
        if str(obj.get('symbol','')).upper()==PAIR:return obj
        for v in obj.values():
            x=find_pair(v)
            if x is not None:return x
    elif isinstance(obj,list):
        for v in obj:
            x=find_pair(v)
            if x is not None:return x
    return None

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-dir',type=Path,required=True); a=ap.parse_args(); out=a.output_dir; out.mkdir(parents=True,exist_ok=True)
    instrument=req(INSTRUMENT_URL)
    pair=None
    if instrument.get('http_status')==200:
        try: pair=find_pair(json.loads(instrument['body']))
        except Exception: pair=None
    tx_probe=req(TX_URL,'POST',{'tonce':0,'ccy':'USDGO','max':1})
    docs=[req(u) for u in DOC_URLS]
    for row in [instrument,tx_probe,*docs]: row.pop('body',None)
    identity_ok=pair is not None
    historical_public=False
    qa=False
    status='FAIL_CLOSED_NO_PUBLIC_HISTORICAL_EXECUTION_TAPE'
    if instrument.get('error'):
        status='FAIL_CLOSED_SOURCE_OR_PARSE'
    elif not identity_ok:
        status='FAIL_CLOSED_EXACT_PAIR_NOT_PUBLICLY_RESOLVED'
    summary={
      'schema_version':'GATE_BTC_2_V2A_USDGO_OSL_QUALIFICATION_V1',
      'symbol':'USDGO','provider':'OSL_GLOBAL_PRO_TRADE','source_symbol':'USDGO/USD','pair_code':PAIR,
      'frozen_window_start_utc':'2026-08-03','frozen_window_end_utc':'2026-09-04','required_daily_buckets':33,
      'instrument_probe':instrument,'transaction_history_probe':tx_probe,'official_document_probes':docs,
      'exact_pair_publicly_resolved':identity_ok,'public_historical_execution_tape_resolved':historical_public,
      'daily_bucket_count':0,'missing_days_count':33,'qa_pass':qa,'status':status,
      'qualification_only':True,'source_admitted':False,'registry_mutated':False,'denominator_changed':False,
      'historical_credit':0,'scientific_credit':False,'prospective_credit':False,'d0_credit':0,'d0_started':False,
      'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders_generated':0,'real_capital_brl':0,
      'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True,
      'reason':'OSL exact USDGO/USD identity may be public/current, but no free/public/auditable historical execution tape sufficient to reconstruct the frozen 33 UTC daily buckets is available through the tested official surface; authenticated account transaction history cannot substitute for public venue history.'
    }
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
