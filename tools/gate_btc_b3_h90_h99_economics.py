#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np,pandas as pd
import gate_btc_b3_h30_h39_cross_asset as b
import gate_btc_b3_h90_h99_official_recovery as src

FAMS=('H93','H94','H96')
THRESHOLDS=(1.0,1.5)
HORIZONS=(60,120)
ASSETS=('WIN','WDO')
GEN='H90_H99_V1'


def signal_frame(values,sessions):
    d=pd.DataFrame(sorted(values.items()),columns=['date','value'])
    d['date']=pd.to_datetime(d['date']); d['value']=pd.to_numeric(d['value'])
    d=d.sort_values('date')
    d['move']=d['value'].diff()
    d['scale']=d['move'].abs().shift(1).rolling(20,min_periods=20).median()
    d['z']=d['move']/d['scale']
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))})
    j=pd.merge_asof(left.sort_values('session'),d[['date','move','z']].sort_values('date'),left_on='session',right_on='date',direction='backward',allow_exact_matches=False)
    j['age_days']=(j['session']-j['date']).dt.days
    j=j[(j.age_days>=1)&(j.age_days<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples() if pd.notna(r.z) and pd.notna(r.move)}


def add(rows,fam,s,g,asset,side,h,param,bar):
    entry=0; exit_i=entry+h//bar; de=1; dx=de+h//bar
    col=f'open_{asset}'
    if exit_i>=len(g): return
    gross=b.rb(side,float(g.iloc[entry][col]),float(g.iloc[exit_i][col]))
    delay=b.rb(side,float(g.iloc[de][col]),float(g.iloc[dx][col])) if dx<len(g) else np.nan
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
            mappings=(('continuation',sign),('reversal',-sign)) if fam=='H96' else (('same',sign),('opposite',-sign))
            for asset in ASSETS:
                for label,side in mappings:
                    for h in HORIZONS:
                        add(rows,fam,s,g,asset,side,h,f'{label}_{th}',bar)
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


def fetch_values(fam):
    if fam=='H93':
        x=src.treasury_series('daily_treasury_real_yield_curve')
        return x['values'],{'status':x['status'],'rows':x['rows'],'years':x['years'],'kind':'US_TREASURY_REAL_10Y'}
    if fam=='H94':
        r=src.treasury_series('daily_treasury_real_yield_curve'); n=src.treasury_series('daily_treasury_yield_curve')
        common=sorted(set(r['values'])&set(n['values'])); vals={d:n['values'][d]-r['values'][d] for d in common}
        ok=(r['status']=='PASS_SOURCE_QA' and n['status']=='PASS_SOURCE_QA' and len(vals)>=1000)
        return vals,{'status':'PASS_SOURCE_QA' if ok else 'DATA_GAP','rows':len(vals),'kind':'DERIVED_TREASURY_10Y_BREAKEVEN'}
    if fam=='H96':
        s=src.nyfed('sofr',True); e=src.nyfed('effr',False); common=sorted(set(s.get('values',{}))&set(e.get('values',{}))); vals={d:s['values'][d]-e['values'][d] for d in common}
        ok=(s['status']=='PASS_SOURCE_QA' and e['status']=='PASS_SOURCE_QA' and len(vals)>=1000)
        return vals,{'status':'PASS_SOURCE_QA' if ok else 'DATA_GAP','rows':len(vals),'kind':'DERIVED_NYFED_SOFR_MINUS_EFFR'}
    raise ValueError(fam)


def main(out,ledger,cells):
    ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    disc={}; repl={}; states={}; sources={}; allcells=[]
    for fam in FAMS:
        try:
            vals,meta=fetch_values(fam); sources[fam]=meta
            if meta['status']!='PASS_SOURCE_QA':
                states[fam]='DATA_GAP'; disc[fam]={'survives':False,'qualified_cells':0,'surviving_legs':[],'qualified':[]}; repl[fam]=disc[fam]; continue
            D,dc=summarize(generate(ds,5,signal_frame(vals,ds),fam),fam)
            R,rc=summarize(generate(rs,15,signal_frame(vals,rs),fam),fam)
            disc[fam]=D; repl[fam]=R
            for z in dc: z['sample']='DISCOVERY'; allcells.append(z)
            for z in rc: z['sample']='REPLICATION'; allcells.append(z)
            states[fam]='SURVIVOR_REPLICATED' if D['survives'] and R['survives'] else 'REJECTED_FAILED_REPLICATION' if D['survives'] else 'REJECTED_DISCOVERY'
        except Exception as e:
            states[fam]='DATA_GAP'; sources[fam]={'status':'DATA_GAP_FETCH','error':type(e).__name__+': '+str(e)[:220]}; disc[fam]={'survives':False,'qualified_cells':0,'surviving_legs':[],'qualified':[]}; repl[fam]=disc[fam]
    survivors=[f for f in FAMS if states[f]=='SURVIVOR_REPLICATED'][:2]
    p={'schema':'gate_btc.b3.h90_h99.economics.v1','status':'PARTIAL_GENERATION_SURVIVORS' if survivors else 'PARTIAL_GENERATION_NO_SURVIVOR','cutoff_exclusive':'2026-08-10','tested_families':list(FAMS),'untested_data_gap_families':['H90','H91','H92','H95','H97','H98','H99'],'states':states,'discovery':disc,'replication':repl,'survivors':survivors,'sources':sources,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dcov)) if dcov else 0,'replication_median_common_bar_coverage':float(np.median(rcov)) if rcov else 0,'h1_economics_read':False,'survivor_partial_economics_read':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False,'not_approved':True}
    Path(out).parent.mkdir(parents=True,exist_ok=True); Path(out).write_text(json.dumps(p,indent=2,sort_keys=True))
    with Path(ledger).open('w') as fh:
        for fam in FAMS: fh.write(json.dumps({'family':fam,'generation':GEN,'state':states[fam],'discovery':disc[fam],'replication':repl[fam],'source':sources[fam],'orders':0,'capital':0,'engine_feed':False,'not_approved':True},sort_keys=True)+'\n')
    pd.DataFrame(allcells).to_csv(cells,index=False)
    print(json.dumps(p,indent=2,sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); z=a.parse_args(); main(z.out,z.ledger,z.cells)
