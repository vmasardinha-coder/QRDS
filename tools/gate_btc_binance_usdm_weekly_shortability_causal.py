#!/usr/bin/env python3
"""Causal Binance USD-M weekly shortability evidence for Friday entry.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
Uses only Binance Data Vision historical 1d kline archive listings.
Positive evidence requires BOTH Thursday (pre-entry existence) and Friday
(entry-day trading) archives. It deliberately does not inspect Saturday.
No authentication, orders, capital, or current exchangeInfo backfill.
"""
from __future__ import annotations

import argparse
import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from gate_btc_binance_usdm_weekly_shortability import (
    SYMBOL_ROOT,
    discover_futures_symbols,
    fridays,
    normalize_asset,
    symbol_daily_dates,
)


def build(start: date, end: date, out_csv: Path, out_summary: Path, workers: int = 16) -> dict:
    completed_end=min(end,datetime.now(timezone.utc).date()-timedelta(days=1))
    eligible=list(fridays(start,completed_end))
    if not eligible:
        raise RuntimeError('no completed Friday in requested interval')
    with requests.Session() as s:
        s.headers.update({'User-Agent':'GATE-BTC-causal-shortability/1.0'})
        symbols=discover_futures_symbols(s)
    if not symbols:
        raise RuntimeError('no USD-M perpetual symbol directories discovered')
    by_symbol={}; errors={}
    fetch_start=eligible[0]-timedelta(days=1)
    fetch_end=eligible[-1]
    with ThreadPoolExecutor(max_workers=max(1,workers)) as ex:
        futs={ex.submit(symbol_daily_dates,sym,fetch_start,fetch_end):sym for sym in symbols}
        for fut in as_completed(futs):
            sym,dates,err=fut.result()
            if err: errors[sym]=err
            else: by_symbol[sym]=dates
    if errors:
        sample=dict(list(sorted(errors.items()))[:10])
        raise RuntimeError(f'symbol archive listing errors={len(errors)} sample={sample}')
    rows=[]; summaries=[]
    for fri in eligible:
        thu=fri-timedelta(days=1); assets=set(); contracts=0
        for sym,dates in sorted(by_symbol.items()):
            if thu not in dates or fri not in dates:
                continue
            asset=normalize_asset(sym); assets.add(asset); contracts+=1
            rows.append({
                'friday_utc':fri.isoformat(),
                'futures_symbol':sym,
                'asset':asset,
                'thursday_archive':True,
                'friday_archive':True,
                'shortable_positive_evidence':True,
            })
        summaries.append({'friday_utc':fri.isoformat(),'futures_contracts':contracts,'normalized_assets':len(assets)})
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    fields=['friday_utc','futures_symbol','asset','thursday_archive','friday_archive','shortable_positive_evidence']
    with out_csv.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    nonempty=sum(x['normalized_assets']>0 for x in summaries)
    payload={
        'status':'PASS' if rows and nonempty==len(summaries) else 'FAIL_INCOMPLETE_HISTORY',
        'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ORDERS':0,'REAL_CAPITAL':0,
        'source':'Binance Data Vision public S3 archive: USD-M daily 1d klines',
        'source_root':SYMBOL_ROOT,
        'method':'causal existence proof for Friday entry = Thursday AND Friday 1d archive files exist; Saturday is never inspected',
        'contract_filter':"USD-M symbol directory; exclude '_' delivery symbols; keep USDT/USDC quotes",
        'absence_policy':'FAIL_CLOSED; current exchangeInfo never backfills historical shortability',
        'start':start.isoformat(),'end':end.isoformat(),'last_evidence_friday':eligible[-1].isoformat(),
        'fridays':len(summaries),'discovered_perpetual_symbols':len(symbols),'ledger_rows':len(rows),'dates':summaries,
    }
    out_summary.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return payload


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--start',default='2020-07-03')
    p.add_argument('--end',default=None)
    p.add_argument('--workers',type=int,default=16)
    p.add_argument('--output-csv',default='artifacts/binance_shortability_causal/BINANCE_USDM_WEEKLY_SHORTABLE_CAUSAL.csv')
    p.add_argument('--output-summary',default='artifacts/binance_shortability_causal/BINANCE_USDM_WEEKLY_SHORTABLE_CAUSAL_SUMMARY.json')
    a=p.parse_args(); start=date.fromisoformat(a.start)
    end=date.fromisoformat(a.end) if a.end else datetime.now(timezone.utc).date()-timedelta(days=1)
    if end<start: raise SystemExit('end before start')
    r=build(start,end,Path(a.output_csv),Path(a.output_summary),a.workers)
    print(json.dumps({k:r[k] for k in ['status','fridays','ledger_rows','ORDERS','REAL_CAPITAL']}))
    return 0 if r['status']=='PASS' else 2

if __name__=='__main__': raise SystemExit(main())
