#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
import gate_btc_b3_h30_h39_cross_asset as b
import gate_btc_b3_h60_h69_data_probe as q
import gate_btc_b3_h62_vix_recovery as v

THRESHOLDS=(0.75,1.0)
HORIZONS=(60,120)
MAPPINGS=('CONTINUE','REVERSE')
ASSETS=('WIN','WDO')
SOURCES=('USDBRL','VIX','US10Y')


def load_source(name):
    if name=='USDBRL':
        meta,x=q.fetch_bcb_brlusd(); return meta,x,'pct'
    if name=='VIX':
        meta,x=v.fetch_vix(); return meta,x,'abs'
    if name=='US10Y':
        meta,x=q.fetch_treasury_10y(); return meta,x,'abs'
    raise ValueError(name)


def persistence_signals(x,sessions,kind):
    d=x[['date','value']].copy().sort_values('date')
    d['move']=d['value'].pct_change() if kind=='pct' else d['value'].diff()
    d['prev_move']=d['move'].shift(1)
    d['scale']=d['move'].abs().shift(1).rolling(20,min_periods=20).median()
    d['z']=d['move']/d['scale']
    d['persist']=(np.sign(d['move'])==np.sign(d['prev_move'])) & d['move'].ne(0) & d['prev_move'].ne(0)
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session')
    j=pd.merge_asof(left,d[['date','move','z','persist']].sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    j['age_days']=(j.session-j.date).dt.days
    j=j[(j.age_days>=1)&(j.age_days<=5)&j.persist.fillna(False)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def add(rows,s,g,source,asset,side,h,param,bar):
    entry=0; exit_i=h//bar; dentry=1; dexit=dentry+h//bar
    if exit_i>=len(g): return
    col=f'open_{asset}'
    gross=b.rb(side,float(g.iloc[entry][col]),float(g.iloc[exit_i][col]))
    delay=b.rb(side,float(g.iloc[dentry][col]),float(g.iloc[dexit][col])) if dexit<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family='H66',session=s,source=source,asset=asset,side=side,param=param,horizon=h,gross=gross,delay=delay))


def generate(ss,bar,source,signals):
    rows=[]
    for s,g in ss.items():
        sig=signals.get(s)
        if sig is None: continue
        z=float(sig.z); mv=float(sig.move)
        if not math.isfinite(z) or not math.isfinite(mv) or mv==0: continue
        sign=1 if mv>0 else -1
        for th in THRESHOLDS:
            if abs(z)<th: continue
            for asset in ASSETS:
                for mapping in MAPPINGS:
                    side=sign if mapping=='CONTINUE' else -sign
                    for h in HORIZONS: add(rows,s,g,source,asset,side,h,f'{source}|{mapping}|{th}',bar)
    return pd.DataFrame(rows)


def summarize(t):
    cells=[]; qualified=[]
    if t.empty: return {'qualified_cells':0,'surviving_source_legs':[],'survives':False,'qualified':[]},cells
    for (source,asset,param,h),g in t.groupby(['source','asset','param','horizon']):
        ok,reasons,m=b.metric(g,*b.COST[asset]); cells.append(dict(family='H66',source=source,asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(reasons),**m))
        if ok: qualified.append((source,asset,param,int(h)))
    legs=[]
    for source in SOURCES:
        for asset in ASSETS:
            qa=[x for x in qualified if x[0]==source and x[1]==asset]
            maps={x[2].split('|')[1] for x in qa}; hs={x[3] for x in qa}; ths={x[2].split('|')[2] for x in qa}
            if len(qa)>=2 and (len(maps)>=2 or len(hs)>=2 or len(ths)>=2): legs.append(f'{source}|{asset}')
    return {'qualified_cells':len(qualified),'surviving_source_legs':sorted(legs),'survives':bool(legs),'qualified':sorted(f'{s}|{a}|{p}|{h}' for s,a,p,h in qualified)},cells


def main(out,ledger,cells):
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    all_d=[]; all_r=[]; sources={}
    for name in SOURCES:
        try:
            meta,x,kind=load_source(name)
            qm=q.qualify(dict(meta),x,pd.DatetimeIndex(pd.to_datetime(sorted(ds))),pd.DatetimeIndex(pd.to_datetime(sorted(rs))))
            sources[name]=qm
            if qm.get('status')!='PASS': continue
            all_d.append(generate(ds,5,name,persistence_signals(x,ds,kind)))
            all_r.append(generate(rs,15,name,persistence_signals(x,rs,kind)))
        except Exception as exc:
            sources[name]={'status':'DATA_GAP_FETCH','error':type(exc).__name__+': '+str(exc)}
    td=pd.concat(all_d,ignore_index=True) if all_d else pd.DataFrame(); tr=pd.concat(all_r,ignore_index=True) if all_r else pd.DataFrame()
    D,dc=summarize(td); R,rc=summarize(tr)
    dlegs=set(D['surviving_source_legs']); rlegs=set(R['surviving_source_legs']); replicated=sorted(dlegs & rlegs)
    state='SURVIVOR_REPLICATED' if replicated else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
    p={'schema':'gate_btc.b3.h66.persistence.v1','family':'H66','state':state,'cutoff_exclusive':'2026-08-10','sources':sources,'thresholds':list(THRESHOLDS),'mappings':list(MAPPINGS),'horizons':list(HORIZONS),'discovery':D,'replication':R,'replicated_source_legs':replicated,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'h1_economics_read':False,'survivor_partial_economics_read':False,'synthetic_backfill':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n')
    Path(ledger).write_text(json.dumps({'family':'H66','generation':'H60_H69_V1','state':state,'replicated_source_legs':replicated,'sources':sources,'orders':0,'capital':0,'engine_feed':False},sort_keys=True)+'\n')
    pd.DataFrame([dict(sample='DISCOVERY',**x) for x in dc]+[dict(sample='REPLICATION',**x) for x in rc]).to_csv(cells,index=False)
    print(json.dumps({'state':state,'replicated_source_legs':replicated,'source_status':{k:v.get('status') for k,v in sources.items()}},sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); z=a.parse_args(); main(z.out,z.ledger,z.cells)
