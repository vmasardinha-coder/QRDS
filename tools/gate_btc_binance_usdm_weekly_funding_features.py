#!/usr/bin/env python3
"""Build causal weekly Binance USD-M funding/crowding features.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
Public Binance Data Vision archives only. No authentication, orders or capital.

Features are computed at Thursday 23:59:59 UTC using only funding events whose
calc_time is <= that cutoff. A canonical contract is chosen causally among
contracts for the same normalized asset that have at least one event in the
trailing 30 days. Priority is deterministic and return-independent:
USDT quote before USDC, non-multiplier before multiplier, then lexical symbol.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import statistics
import time
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import requests

S3_BASES=(
    "https://s3.ap-northeast-1.amazonaws.com/data.binance.vision",
    "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision",
)
DIRECT_BASE="https://data.binance.vision/data/futures/um/monthly/fundingRate"
ROOT="data/futures/um/monthly/fundingRate/"
NS={"s3":"http://s3.amazonaws.com/doc/2006-03-01/"}
QUOTE_SUFFIXES=("USDT","USDC")
MULTIPLIERS=("1000000","1000","1M")
YM_RE=re.compile(r"-(\d{4}-\d{2})\.zip$")
ALIASES={"LUNA2":"LUNA","BEAMX":"BEAM","DODOX":"DODO"}


def normalize_asset(symbol:str)->str:
    s=symbol.upper().strip()
    for q in QUOTE_SUFFIXES:
        if s.endswith(q):
            s=s[:-len(q)]; break
    for p in MULTIPLIERS:
        if s.startswith(p) and len(s)>len(p):
            s=s[len(p):]; break
    return ALIASES.get(s,s)


def contract_priority(symbol:str)->tuple:
    s=symbol.upper()
    quote=0 if s.endswith("USDT") else 1
    base=s[:-4] if s.endswith("USDT") else s[:-4] if s.endswith("USDC") else s
    multiplied=1 if any(base.startswith(p) for p in MULTIPLIERS) else 0
    return (quote,multiplied,len(s),s)


def thursdays(start:date,end:date)->Iterable[date]:
    d=start
    while d.weekday()!=3:
        d+=timedelta(days=1)
    while d<=end:
        yield d; d+=timedelta(days=7)


def cutoff_ms(d:date)->int:
    x=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)+timedelta(days=1)-timedelta(milliseconds=1)
    return int(x.timestamp()*1000)


def _request_xml(session:requests.Session,params:dict,retries:int=5)->ET.Element:
    last=None
    for attempt in range(retries):
        for base in S3_BASES:
            try:
                r=session.get(base,params=params,timeout=45)
                if r.status_code==200:
                    return ET.fromstring(r.content)
                last=RuntimeError(f"S3 HTTP {r.status_code}: {r.url}")
            except Exception as exc:
                last=exc
        time.sleep(min(0.5*(2**attempt),5.0))
    raise RuntimeError(f"S3 listing failed: {last}")


def list_common_prefixes(session:requests.Session,prefix:str)->list[str]:
    out=[]; token=None
    while True:
        params={"list-type":"2","prefix":prefix,"delimiter":"/","max-keys":"1000"}
        if token: params["continuation-token"]=token
        root=_request_xml(session,params)
        out.extend(x.text or "" for x in root.findall("s3:CommonPrefixes/s3:Prefix",NS))
        truncated=root.findtext("s3:IsTruncated",default="false",namespaces=NS).lower()=="true"
        if not truncated: break
        token=root.findtext("s3:NextContinuationToken",default="",namespaces=NS)
        if not token: raise RuntimeError("truncated listing without token")
    return out


def list_keys(session:requests.Session,prefix:str)->list[str]:
    out=[]; token=None
    while True:
        params={"list-type":"2","prefix":prefix,"max-keys":"1000"}
        if token: params["continuation-token"]=token
        root=_request_xml(session,params)
        out.extend(x.text or "" for x in root.findall("s3:Contents/s3:Key",NS))
        truncated=root.findtext("s3:IsTruncated",default="false",namespaces=NS).lower()=="true"
        if not truncated: break
        token=root.findtext("s3:NextContinuationToken",default="",namespaces=NS)
        if not token: raise RuntimeError("truncated key listing without token")
    return out


def discover_symbols(session:requests.Session)->list[str]:
    syms=[]
    for p in list_common_prefixes(session,ROOT):
        sym=p[len(ROOT):].strip("/").upper() if p.startswith(ROOT) else ""
        if sym and "_" not in sym and sym.endswith(QUOTE_SUFFIXES): syms.append(sym)
    return sorted(set(syms))


def _to_ms(v:str)->int:
    x=int(float(v))
    while x>10**14: x//=1000
    return x


def parse_zip(blob:bytes)->list[tuple[int,float]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=[n for n in z.namelist() if not n.endswith('/')]
        if not names: return []
        raw=z.read(names[0]).decode('utf-8-sig',errors='replace')
    rows=list(csv.reader(io.StringIO(raw)))
    if not rows: return []
    header=[x.strip().lower() for x in rows[0]]
    has_header=True
    try: float(rows[0][0]); has_header=False
    except Exception: pass
    if has_header:
        body=rows[1:]
        time_names=['calc_time','fundingtime','funding_time','calctime','time','timestamp']
        rate_names=['last_funding_rate','fundingrate','funding_rate','rate']
        ti=next((header.index(x) for x in time_names if x in header),0)
        ri=next((header.index(x) for x in rate_names if x in header),len(header)-1)
    else:
        body=rows; ti=0; ri=len(rows[0])-1
    out=[]
    for row in body:
        if len(row)<=max(ti,ri): continue
        try: out.append((_to_ms(row[ti]),float(row[ri])))
        except Exception: continue
    return out


def fetch_month(symbol:str,ym:str)->tuple[str,str,list[tuple[int,float]],str|None]:
    url=f"{DIRECT_BASE}/{symbol}/{symbol}-fundingRate-{ym}.zip"
    try:
        r=requests.get(url,timeout=45,headers={'User-Agent':'GATE-BTC-funding-features/1.0'})
        if r.status_code==404: return symbol,ym,[],None
        r.raise_for_status()
        return symbol,ym,parse_zip(r.content),None
    except Exception as exc:
        return symbol,ym,[],repr(exc)


def build(start:date,end:date,out_csv:Path,out_summary:Path,workers:int=24)->dict:
    # Need 30d trailing history before first requested Thursday.
    fetch_start=start-timedelta(days=35)
    with requests.Session() as s:
        s.headers.update({'User-Agent':'GATE-BTC-funding-features/1.0'})
        symbols=discover_symbols(s)
        if not symbols: raise RuntimeError('no fundingRate symbol directories discovered')
        symbol_keys={}
        for sym in symbols:
            symbol_keys[sym]=list_keys(s,f"{ROOT}{sym}/")

    jobs=[]
    for sym,keys in symbol_keys.items():
        for key in keys:
            if not key.endswith('.zip') or key.endswith('.zip.CHECKSUM'): continue
            m=YM_RE.search(key)
            if not m: continue
            ym=m.group(1)
            first=date.fromisoformat(ym+'-01')
            nextm=(first.replace(day=28)+timedelta(days=4)).replace(day=1)
            last=nextm-timedelta(days=1)
            if last<fetch_start or first>end: continue
            jobs.append((sym,ym))

    events_by_symbol={s:[] for s in symbols}; errors=[]
    with ThreadPoolExecutor(max_workers=max(1,workers)) as ex:
        futs=[ex.submit(fetch_month,s,ym) for s,ym in jobs]
        for fut in as_completed(futs):
            sym,ym,ev,err=fut.result()
            if err: errors.append({'symbol':sym,'month':ym,'error':err})
            events_by_symbol.setdefault(sym,[]).extend(ev)
    if errors:
        raise RuntimeError(f"funding archive download errors={len(errors)} sample={errors[:10]}")
    for s in events_by_symbol: events_by_symbol[s].sort()

    by_asset={}
    for sym,ev in events_by_symbol.items():
        if ev: by_asset.setdefault(normalize_asset(sym),[]).append((sym,ev))

    rows=[]; date_summary=[]
    for d in thursdays(start,end):
        cut=cutoff_ms(d); lo30=cut-30*86400000; lo7=cut-7*86400000
        n_assets=0
        for asset,contracts in by_asset.items():
            active=[]
            for sym,ev in contracts:
                recent=[(t,r) for t,r in ev if lo30<t<=cut]
                if recent: active.append((contract_priority(sym),sym,recent))
            if not active: continue
            active.sort(key=lambda x:x[0]); _,sym,recent30=active[0]
            rates30=[r for _,r in recent30]
            rates7=[r for t,r in recent30 if lo7<t<=cut]
            last_t,last_r=max(recent30,key=lambda x:x[0])
            rows.append({
                'signal_date':d.isoformat(),'asset':asset,'futures_symbol':sym,
                'fund_last':last_r,
                'fund_mean_7d':(sum(rates7)/len(rates7) if rates7 else ''),
                'fund_mean_30d':sum(rates30)/len(rates30),
                'fund_std_30d':(statistics.stdev(rates30) if len(rates30)>1 else 0.0),
                'fund_events_7d':len(rates7),'fund_events_30d':len(rates30),
                'fund_last_time_ms':last_t,
            }); n_assets+=1
        date_summary.append({'signal_date':d.isoformat(),'assets_with_funding_features':n_assets})

    out_csv.parent.mkdir(parents=True,exist_ok=True)
    fields=['signal_date','asset','futures_symbol','fund_last','fund_mean_7d','fund_mean_30d','fund_std_30d','fund_events_7d','fund_events_30d','fund_last_time_ms']
    with out_csv.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    payload={
      'status':'PASS' if rows else 'FAIL_NO_ROWS',
      'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ORDERS':0,'REAL_CAPITAL':0,
      'source':'Binance Data Vision monthly USD-M fundingRate archive',
      'causality':'all funding event calc_time <= Thursday 23:59:59 UTC',
      'features':['fund_last','fund_mean_7d','fund_mean_30d','fund_std_30d'],
      'canonical_contract_policy':'trailing-30d active; USDT>USDC; non-multiplier>multiplier; lexical tie-break',
      'start':start.isoformat(),'end':end.isoformat(),'thursdays':len(date_summary),
      'discovered_symbols':len(symbols),'downloaded_symbol_months':len(jobs),'rows':len(rows),
      'dates':date_summary,
    }
    out_summary.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return payload


def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--start',default='2021-01-07')
    p.add_argument('--end',default='2024-12-31')
    p.add_argument('--workers',type=int,default=24)
    p.add_argument('--output-csv',default='artifacts/binance_funding_features/BINANCE_USDM_WEEKLY_FUNDING_FEATURES.csv')
    p.add_argument('--output-summary',default='artifacts/binance_funding_features/BINANCE_USDM_WEEKLY_FUNDING_FEATURES_SUMMARY.json')
    a=p.parse_args(); start=date.fromisoformat(a.start); end=date.fromisoformat(a.end)
    if end<start: raise SystemExit('end before start')
    r=build(start,end,Path(a.output_csv),Path(a.output_summary),a.workers)
    print(json.dumps({k:r[k] for k in ['status','thursdays','downloaded_symbol_months','rows','ORDERS','REAL_CAPITAL']}))
    return 0 if r['status']=='PASS' else 2

if __name__=='__main__': raise SystemExit(main())
