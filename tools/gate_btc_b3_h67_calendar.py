#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import gate_btc_b3_h30_h39_cross_asset as b

CUTOFF='2026-08-10'
ASSETS=('WIN','WDO')
HORIZONS=(60,120)
MAPPINGS=('CONTINUE','FADE')
PARSER_VERSION='h67-calendar-v1'
OFFICIAL_SOURCES={
    'FOMC_2019':'https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm',
    'FOMC_2020':'https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm',
    'FOMC_2021_2027':'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm',
    'COPOM_ALL':'https://www.bcb.gov.br/en/about/bcb-calendar?categoria=Monetary%20Policy%20Committee%20%28Copom%29&periodo=All',
}


def fetch_official():
    out={}
    for name,url in OFFICIAL_SOURCES.items():
        try:
            r=requests.get(url,timeout=(10,45),headers={'User-Agent':'QRDS-research/1.0'})
            r.raise_for_status(); raw=r.content
            if len(raw)<500: raise ValueError('implausibly small official response')
            out[name]={'status':'FETCHED','url':r.url,'provider':'Federal Reserve Board' if name.startswith('FOMC') else 'Banco Central do Brasil','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'parser_version':PARSER_VERSION}
        except Exception as exc:
            out[name]={'status':'DATA_GAP','url':url,'error_type':type(exc).__name__,'error':str(exc)[:400],'parser_version':PARSER_VERSION}
    return out


def session_dates(ss):
    return sorted(pd.Timestamp(k).date() for k in ss)


def derived_flags(ss):
    dates=session_dates(ss)
    by_month=defaultdict(list)
    for d in dates: by_month[(d.year,d.month)].append(d)
    month_turn=set()
    for vals in by_month.values():
        month_turn.add(vals[0]); month_turn.add(vals[-1])
    weekday_edge={d for d in dates if d.weekday() in (0,4)}
    return {'MONTH_TURN':month_turn,'WEEKDAY_EDGE':weekday_edge}


def add(rows,fam,s,g,asset,side,horizon,param,bar):
    entry=30//bar; exit_i=entry+horizon//bar; dentry=entry+1; dexit=dentry+horizon//bar
    if exit_i>=len(g): return
    col=f'open_{asset}'
    gross=b.rb(side,float(g.iloc[entry][col]),float(g.iloc[exit_i][col]))
    delay=b.rb(side,float(g.iloc[dentry][col]),float(g.iloc[dexit][col])) if dexit<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family=fam,session=s,asset=asset,side=side,param=param,horizon=horizon,gross=gross,delay=delay))


def generate(ss,bar,flags):
    rows=[]
    for s,g in ss.items():
        d=pd.Timestamp(s).date()
        active=[name for name,vals in flags.items() if d in vals]
        if not active: continue
        entry=30//bar
        if entry>=len(g): continue
        for asset in ASSETS:
            col=f'open_{asset}'
            first=float(g.iloc[0][col]); after=float(g.iloc[entry][col])
            if not (math.isfinite(first) and math.isfinite(after)) or after==first: continue
            sign=1 if after>first else -1
            for flag in active:
                for mapping in MAPPINGS:
                    side=sign if mapping=='CONTINUE' else -sign
                    for h in HORIZONS:
                        add(rows,'H67',s,g,asset,side,h,f'{flag}|{mapping}',bar)
    return pd.DataFrame(rows)


def summarize(t):
    q=[]; cells=[]
    if t.empty: return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (asset,param,h),g in t.groupby(['asset','param','horizon']):
        ok,reasons,m=b.metric(g,*b.COST[asset]); cells.append(dict(family='H67',asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(reasons),**m))
        if ok: q.append((asset,param,int(h)))
    legs=[]
    for asset in ASSETS:
        qa=[x for x in q if x[0]==asset]
        mappings={x[1].split('|')[1] for x in qa}
        horizons={x[2] for x in qa}
        if len(qa)>=2 and (len(mappings)>=2 or len(horizons)>=2): legs.append(asset)
    return {'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)},cells


def main(out,cells):
    official=fetch_official()
    # Event-day flags stay fail-closed until a deterministic date parser/coverage attestation is separately green.
    flag_status={
        'FOMC_DECISION_DAY':{'status':'DATA_GAP','reason':'official pages fetched/probed but deterministic historical date extraction/coverage attestation not yet frozen'},
        'COPOM_DECISION_DAY':{'status':'DATA_GAP','reason':'official calendar fetched/probed but deterministic historical date extraction/coverage attestation not yet frozen'},
        'MONTH_TURN':{'status':'DATA_READY','source':'derived causally from observed B3 session dates'},
        'WEEKDAY_EDGE':{'status':'DATA_READY','source':'derived causally from observed B3 session dates'},
    }
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    D,dc=summarize(generate(ds,5,derived_flags(ds)))
    R,rc=summarize(generate(rs,15,derived_flags(rs)))
    state='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
    report={
      'schema':'gate_btc.b3.h67.calendar.v1','cutoff_exclusive':CUTOFF,'family':'H67','state':state,
      'official_source_probe':official,'flag_status':flag_status,'tested_flags':['MONTH_TURN','WEEKDAY_EDGE'],
      'untested_data_gap_flags':['FOMC_DECISION_DAY','COPOM_DECISION_DAY'],'discovery':D,'replication':R,
      'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),
      'h1_economics_read':False,'survivor_partial_economics_read':False,'synthetic_backfill':False,
      'orders_generated':0,'real_capital_used':0,'engine_feed':False
    }
    Path(out).write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    pd.DataFrame([dict(sample='DISCOVERY',**x) for x in dc]+[dict(sample='REPLICATION',**x) for x in rc]).to_csv(cells,index=False)
    print(json.dumps({'state':state,'official':{k:v['status'] for k,v in official.items()},'flags':flag_status},sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--out',required=True); p.add_argument('--cells',required=True); a=p.parse_args(); main(a.out,a.cells)
