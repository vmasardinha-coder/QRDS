#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, math, re, time
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF = pd.Timestamp('2026-08-10')
THRESHOLDS = (1.0, 1.5)
HORIZONS = (60, 120)
MAPPINGS = ('same', 'opposite')
ASSETS = ('WIN', 'WDO')
SERIES = {'H61': ('SP500','SP500'), 'H64': ('WTI','DCOILWTICO')}


def http_session():
    retry = Retry(total=3, connect=3, read=3, status=3, redirect=2, backoff_factor=1.5,
                  status_forcelist=(429,500,502,503,504), allowed_methods=frozenset(['GET']))
    s = requests.Session(); s.mount('https://', HTTPAdapter(max_retries=retry)); return s


def parse_fred(raw):
    z = pd.read_csv(StringIO(raw.decode('utf-8-sig')))
    if z.shape[1] < 2:
        raise ValueError('unexpected FRED schema')
    z = z.iloc[:, :2].copy(); z.columns = ['date','value']
    z['date'] = pd.to_datetime(z['date'], errors='coerce')
    z['value'] = pd.to_numeric(z['value'], errors='coerce')
    z = z.dropna().sort_values('date').drop_duplicates('date')
    z = z[(z.date >= pd.Timestamp('2019-01-01')) & (z.date < CUTOFF)]
    if z.empty or not z.date.is_monotonic_increasing or z.date.duplicated().any():
        raise ValueError('invalid/empty FRED series')
    return z


def parse_fred_static(raw):
    text = raw.decode('utf-8-sig', errors='replace')
    rows=[]
    for line in text.splitlines():
        m=re.match(r'^\s*(\d{4}-\d{2}-\d{2})\s+([^\s]+)\s*$', line)
        if not m:
            continue
        value=pd.to_numeric(m.group(2), errors='coerce')
        if pd.notna(value):
            rows.append((m.group(1), float(value)))
    if not rows:
        raise ValueError('unexpected/empty FRED static data')
    z=pd.DataFrame(rows, columns=['date','value'])
    z['date']=pd.to_datetime(z['date'], errors='coerce')
    z=z.dropna().sort_values('date').drop_duplicates('date')
    z=z[(z.date >= pd.Timestamp('2019-01-01')) & (z.date < CUTOFF)]
    if z.empty or not z.date.is_monotonic_increasing or z.date.duplicated().any():
        raise ValueError('invalid/empty FRED static series')
    return z


def fetch_fred(name, series):
    endpoints = [
        ('fredgraph','https://fred.stlouisfed.org/graph/fredgraph.csv',{'id':series,'cosd':'2019-01-01','coed':'2026-08-09'},'csv'),
        ('series_download',f'https://fred.stlouisfed.org/series/{series}/downloaddata/{series}.csv',None,'csv'),
        ('static_data',f'https://fred.stlouisfed.org/data/{series}.txt',None,'txt'),
    ]
    s = http_session(); last = None; attempt = 0
    for round_no in range(3):
        for delivery, url, params, fmt in endpoints:
            attempt += 1
            try:
                r = s.get(url, params=params, timeout=(10,60), headers={'User-Agent':'QRDS-research/1.0'})
                r.raise_for_status(); raw = r.content
                if not raw:
                    raise ValueError('empty FRED response')
                x = parse_fred_static(raw) if fmt == 'txt' else parse_fred(raw)
                meta = {'name':name,'series':series,'provider':'FRED / Federal Reserve Bank of St. Louis',
                        'delivery_path':delivery,'url':r.url,'sha256':hashlib.sha256(raw).hexdigest(),
                        'rows':len(x),'first':x.date.min().date().isoformat(),'last':x.date.max().date().isoformat(),
                        'fetch_attempt':attempt,'format':fmt}
                return meta, x
            except Exception as exc:
                last = exc
        if round_no < 2:
            time.sleep(4 * (round_no + 1))
    raise last if last else RuntimeError('FRED fetch failed')


def coverage(x, sessions):
    d = x[['date','value']].sort_values('date')
    left = pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j = pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    age = (j.session-j.date).dt.days
    ok = j.value.notna() & age.notna() & (age <= 5)
    return float(ok.mean()), int(ok.sum()), int(len(j)), int(age.dropna().max()) if age.notna().any() else None


def causal_signals(x, sessions):
    d = x[['date','value']].copy().sort_values('date')
    d['move'] = d['value'].pct_change()
    d['scale'] = d['move'].abs().shift(1).rolling(20,min_periods=20).median()
    d['z'] = d['move'] / d['scale']
    left = pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j = pd.merge_asof(left,d[['date','move','z']],left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    j['age_days'] = (j.session-j.date).dt.days
    j = j[(j.age_days >= 1) & (j.age_days <= 5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def add(rows, fam, s, g, asset, side, horizon, param, bar):
    entry=0; exit_i=entry+horizon//bar; delay_entry=1; delay_exit=delay_entry+horizon//bar
    if exit_i >= len(g): return
    col=f'open_{asset}'
    gross=b.rb(side,float(g.iloc[entry][col]),float(g.iloc[exit_i][col]))
    delay=b.rb(side,float(g.iloc[delay_entry][col]),float(g.iloc[delay_exit][col])) if delay_exit < len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family=fam,session=s,asset=asset,side=side,param=param,horizon=horizon,gross=gross,delay=delay))


def generate(fam, ss, bar, signals):
    rows=[]
    for s,g in ss.items():
        sig=signals.get(s)
        if sig is None: continue
        z,mv=float(sig.z),float(sig.move)
        if not math.isfinite(z) or not math.isfinite(mv) or mv == 0: continue
        sign=1 if mv>0 else -1
        for th in THRESHOLDS:
            if abs(z)<th: continue
            for asset in ASSETS:
                for mapping in MAPPINGS:
                    side=sign if mapping=='same' else -sign
                    for h in HORIZONS: add(rows,fam,s,g,asset,side,h,f'{mapping}_{th}',bar)
    return pd.DataFrame(rows)


def summarize(fam, t):
    q=[]; cells=[]
    if t.empty: return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (asset,param,h),g in t.groupby(['asset','param','horizon']):
        ok,reasons,m=b.metric(g,*b.COST[asset]); cells.append(dict(family=fam,asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(reasons),**m))
        if ok: q.append((asset,param,int(h)))
    legs=[]
    for asset in ASSETS:
        qa=[x for x in q if x[0]==asset]
        if len(qa)>=2 and (len({x[1] for x in qa})>=2 or len({x[2] for x in qa})>=2): legs.append(asset)
    return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells


def main(out, ledger, cells):
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    results={}; allcells=[]; ledger_rows=[]
    for fam,(name,series) in SERIES.items():
        meta,x=fetch_fred(name,series)
        dcv,dn,dt,dm=coverage(x,ds); rcv,rn,rt,rm=coverage(x,rs)
        meta.update({'discovery_join_coverage':dcv,'replication_join_coverage':rcv,'discovery_join_n':f'{dn}/{dt}','replication_join_n':f'{rn}/{rt}','max_stale_days_discovery':dm,'max_stale_days_replication':rm})
        if dcv < .90 or rcv < .90: raise SystemExit(f'FAIL {fam} coverage below gate')
        meta['status']='PASS'
        D,dc=summarize(fam,generate(fam,ds,5,causal_signals(x,ds))); R,rc=summarize(fam,generate(fam,rs,15,causal_signals(x,rs)))
        state='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
        results[fam]={'state':state,'source':meta,'discovery':D,'replication':R}
        allcells += [dict(sample='DISCOVERY',**z) for z in dc] + [dict(sample='REPLICATION',**z) for z in rc]
        ledger_rows.append({'family':fam,'generation':'H60_H69_V1','state':state,'source':meta,'discovery':D,'replication':R,'orders':0,'capital':0,'engine_feed':False})
    p={'schema':'gate_btc.b3.h61_h64.fred_recovery.v1','cutoff_exclusive':'2026-08-10','results':results,
       'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dcov)) if dcov else 0,
       'replication_median_common_bar_coverage':float(np.median(rcov)) if rcov else 0,'h1_economics_read':False,'survivor_partial_economics_read':False,
       'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True))
    Path(ledger).write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in ledger_rows))
    pd.DataFrame(allcells).to_csv(cells,index=False)
    print(json.dumps(p,indent=2,sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('--ledger',required=True); p.add_argument('--cells',required=True)
    a=p.parse_args(); main(a.out,a.ledger,a.cells)
