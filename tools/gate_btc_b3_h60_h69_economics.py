#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
import gate_btc_b3_h30_h39_cross_asset as b
import gate_btc_b3_h60_h69_data_probe as q

FAMS=('H60','H63')
THRESHOLDS=(1.0,1.5)
HORIZONS=(60,120)
MAPPINGS=('same','opposite')
ASSETS=('WIN','WDO')
GEN='H60_H69_V1'


def causal_signal_frame(x: pd.DataFrame, sessions):
    d=x[['date','value']].copy().sort_values('date')
    d['move']=d['value'].pct_change()
    # For yields use absolute level change rather than pct; caller may overwrite.
    d['scale']=d['move'].abs().shift(1).rolling(20,min_periods=20).median()
    d['z']=d['move']/d['scale']
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))})
    j=pd.merge_asof(left.sort_values('session'),d[['date','move','z']].sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    j['age_days']=(j['session']-j['date']).dt.days
    j=j[(j.age_days>=1)&(j.age_days<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def causal_yield_signal_frame(x: pd.DataFrame, sessions):
    d=x[['date','value']].copy().sort_values('date')
    d['move']=d['value'].diff()
    d['scale']=d['move'].abs().shift(1).rolling(20,min_periods=20).median()
    d['z']=d['move']/d['scale']
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))})
    j=pd.merge_asof(left.sort_values('session'),d[['date','move','z']].sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    j['age_days']=(j['session']-j['date']).dt.days
    j=j[(j.age_days>=1)&(j.age_days<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def add(rows,fam,s,g,asset,side,h,param,bar):
    entry=0; exit_i=entry+h//bar; delay_entry=1; delay_exit=delay_entry+h//bar
    col=f'open_{asset}'
    if exit_i>=len(g): return
    gross=b.rb(side,float(g.iloc[entry][col]),float(g.iloc[exit_i][col]))
    delay=b.rb(side,float(g.iloc[delay_entry][col]),float(g.iloc[delay_exit][col])) if delay_exit<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family=fam,session=s,asset=asset,side=side,param=param,horizon=h,gross=gross,delay=delay))


def generate(ss,bar,signals,fam):
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
                    side=sign if mapping=='same' else -sign
                    for h in HORIZONS:
                        add(rows,fam,s,g,asset,side,h,f'{mapping}_{th}',bar)
    return pd.DataFrame(rows)


def summarize(t,fam):
    qualified=[]; cells=[]
    if t.empty: return {'qualified_cells':0,'surviving_legs':[],'survives':False,'qualified':[]},cells
    for (asset,param,h),g in t.groupby(['asset','param','horizon']):
        ok,re,m=b.metric(g,*b.COST[asset])
        cells.append(dict(family=fam,asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(re),**m))
        if ok: qualified.append((asset,param,int(h)))
    legs=[]
    for asset in ASSETS:
        qa=[x for x in qualified if x[0]==asset]
        ps={x[1] for x in qa}; hs={x[2] for x in qa}
        if len(qa)>=2 and (len(ps)>=2 or len(hs)>=2): legs.append(asset)
    return {'qualified_cells':len(qualified),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in qualified)},cells


def source_for(fam):
    if fam=='H60': return q.fetch_bcb_brlusd(), False
    if fam=='H63': return q.fetch_treasury_10y(), True
    raise ValueError(fam)


def main(out,ledger,cells):
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    disc={}; repl={}; source_meta={}; states={}; allcells=[]
    for fam in FAMS:
        try:
            (meta,x),is_yield=source_for(fam)
            qm=q.qualify(dict(meta),x,pd.DatetimeIndex(pd.to_datetime(sorted(ds))),pd.DatetimeIndex(pd.to_datetime(sorted(rs))))
            source_meta[fam]=qm
            if qm.get('status')!='PASS':
                states[fam]='DATA_GAP'; disc[fam]={'survives':False,'qualified_cells':0,'surviving_legs':[],'qualified':[]}; repl[fam]=disc[fam]; continue
            sigd=(causal_yield_signal_frame if is_yield else causal_signal_frame)(x,ds)
            sigr=(causal_yield_signal_frame if is_yield else causal_signal_frame)(x,rs)
            D,dc=summarize(generate(ds,5,sigd,fam),fam); R,rc=summarize(generate(rs,15,sigr,fam),fam)
            disc[fam]=D; repl[fam]=R
            for z in dc: z['sample']='DISCOVERY'; allcells.append(z)
            for z in rc: z['sample']='REPLICATION'; allcells.append(z)
            states[fam]='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
        except Exception as e:
            source_meta[fam]={'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)}
            disc[fam]={'survives':False,'qualified_cells':0,'surviving_legs':[],'qualified':[]}; repl[fam]=disc[fam]; states[fam]='DATA_GAP'
    survivors=[f for f in FAMS if states[f]=='SURVIVOR_REPLICATED'][:2]
    status='PARTIAL_GENERATION_SURVIVORS' if survivors else 'PARTIAL_GENERATION_NO_SURVIVOR'
    p={'schema':'gate_btc.b3.h60_h69.economics.v1','status':status,'cutoff_exclusive':'2026-08-10','tested_families':list(FAMS),'untested_data_gap_families':['H61','H62','H64','H65','H66','H67','H68','H69'],'states':states,'discovery':disc,'replication':repl,'survivors':survivors,'sources':source_meta,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dcov)) if dcov else 0,'replication_median_common_bar_coverage':float(np.median(rcov)) if rcov else 0,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).parent.mkdir(parents=True,exist_ok=True); Path(out).write_text(json.dumps(p,indent=2,sort_keys=True))
    with Path(ledger).open('w') as fh:
        for fam in FAMS: fh.write(json.dumps({'family':fam,'generation':GEN,'state':states[fam],'discovery':disc[fam],'replication':repl[fam],'source':source_meta[fam],'orders':0,'capital':0,'engine_feed':False},sort_keys=True)+'\n')
    pd.DataFrame(allcells).to_csv(cells,index=False)
    print(json.dumps(p,indent=2,sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); z=a.parse_args(); main(z.out,z.ledger,z.cells)
