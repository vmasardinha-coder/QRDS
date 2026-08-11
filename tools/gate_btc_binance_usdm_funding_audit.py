#!/usr/bin/env python3
"""Audit realized Binance USD-M funding for a frozen short manifest.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. Public Binance Data Vision only.
No authentication, orders or capital. Downloads monthly fundingRate ZIPs and
sums funding events strictly after Friday close through next Friday close.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"


def months_between(a: str, b: str) -> list[str]:
    d = datetime.fromisoformat(a).date().replace(day=1)
    e = datetime.fromisoformat(b).date().replace(day=1)
    out=[]
    while d <= e:
        out.append(f"{d.year:04d}-{d.month:02d}")
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def _to_ms(v: str) -> int:
    x = int(float(v))
    while x > 10**14:
        x //= 1000
    return x


def parse_funding_zip(blob: bytes) -> tuple[list[tuple[int,float]], list[str]]:
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        names=[n for n in z.namelist() if not n.endswith('/')]
        if not names:
            return [], []
        raw=z.read(names[0]).decode('utf-8-sig',errors='replace')
    rows=list(csv.reader(io.StringIO(raw)))
    if not rows:
        return [], []
    first=[x.strip() for x in rows[0]]
    header=None
    try:
        float(first[0])
    except Exception:
        header=[x.strip().lower() for x in first]
        rows=rows[1:]
    if header:
        time_candidates=['calc_time','fundingtime','funding_time','calctime','time','timestamp']
        rate_candidates=['last_funding_rate','fundingrate','funding_rate','rate']
        ti=next((header.index(x) for x in time_candidates if x in header),None)
        ri=next((header.index(x) for x in rate_candidates if x in header),None)
        if ti is None:
            ti=0
        if ri is None:
            ri=len(header)-1
    else:
        ti=0; ri=len(first)-1
    out=[]
    for row in rows:
        if len(row)<=max(ti,ri):
            continue
        try:
            out.append((_to_ms(row[ti]),float(row[ri])))
        except Exception:
            continue
    return out, (header or [])


def fetch_month(session: requests.Session, symbol: str, ym: str) -> tuple[list[tuple[int,float]], list[str], str]:
    url=f"{BASE}/{symbol}/{symbol}-fundingRate-{ym}.zip"
    r=session.get(url,timeout=45)
    if r.status_code==404:
        return [], [], url
    r.raise_for_status()
    events,header=parse_funding_zip(r.content)
    return events,header,url


def close_ms(day: str) -> int:
    d=datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    return int((d + timedelta(days=1) - timedelta(milliseconds=1)).timestamp()*1000)


def audit(manifest: Path, out_csv: Path, out_summary: Path) -> dict:
    with manifest.open(encoding='utf-8') as f:
        positions=list(csv.DictReader(f))
    if not positions:
        raise RuntimeError('empty manifest')
    needed={}
    for p in positions:
        for ym in months_between(p['entry_friday'],p['exit_friday']):
            needed.setdefault(p['futures_symbol'],set()).add(ym)
    cache={}; headers=set(); missing=[]
    with requests.Session() as s:
        s.headers.update({'User-Agent':'GATE-BTC-research-funding/1.0'})
        for symbol in sorted(needed):
            ev=[]
            for ym in sorted(needed[symbol]):
                events,hdr,url=fetch_month(s,symbol,ym)
                if not events:
                    missing.append({'symbol':symbol,'month':ym,'url':url})
                ev.extend(events)
                if hdr: headers.add(tuple(hdr))
            cache[symbol]=sorted(ev)
    rows=[]
    for p in positions:
        lo=close_ms(p['entry_friday'])
        hi=close_ms(p['exit_friday'])
        ev=[(t,r) for t,r in cache.get(p['futures_symbol'],[]) if lo < t <= hi]
        rows.append({**p,'funding_events':len(ev),'funding_rate_sum':sum(r for _,r in ev),
                     'first_event_ms':min((t for t,_ in ev),default=''),
                     'last_event_ms':max((t for t,_ in ev),default='')})
    out_csv.parent.mkdir(parents=True,exist_ok=True)
    with out_csv.open('w',newline='',encoding='utf-8') as f:
        fields=list(rows[0].keys())
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    zero=sum(1 for x in rows if int(x['funding_events'])==0)
    payload={
      'status':'PASS' if zero==0 else 'PASS_WITH_ZERO_EVENT_POSITIONS',
      'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ORDERS':0,'REAL_CAPITAL':0,
      'source':BASE,
      'method':'sum actual archived funding rates for events strictly after entry-Friday close through exit-Friday close',
      'portfolio_application':'short funding PnL approximation = abs(initial short weight) * funding_rate_sum; positive funding benefits short',
      'positions':len(rows),'symbols':len(needed),'symbol_months':sum(len(x) for x in needed.values()),
      'zero_event_positions':zero,'missing_month_files':missing,
      'observed_headers':[list(x) for x in sorted(headers)],
    }
    out_summary.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return payload


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--output-csv',default='artifacts/binance_funding/V9C_FUNDING_AUDIT.csv')
    p.add_argument('--output-summary',default='artifacts/binance_funding/V9C_FUNDING_AUDIT_SUMMARY.json')
    a=p.parse_args()
    r=audit(Path(a.manifest),Path(a.output_csv),Path(a.output_summary))
    print(json.dumps({k:r[k] for k in ['status','positions','symbols','symbol_months','zero_event_positions','ORDERS','REAL_CAPITAL']}))
    return 0 if r['status'].startswith('PASS') else 2

if __name__=='__main__':
    raise SystemExit(main())
