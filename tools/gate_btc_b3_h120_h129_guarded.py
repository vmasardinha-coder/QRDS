#!/usr/bin/env python3
from __future__ import annotations
import argparse, math
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
import pandas as pd
import gate_btc_b3_h120_h129_economics as m


def guarded_daily(days):
    # Mechanical-only acceleration: reuse the exact frozen parse_day contract while
    # increasing concurrent official-B3 fetches. No source, parsing, front selection,
    # provenance/hash, retry, coverage, feature, or economic rule changes here.
    recs=[]
    with ThreadPoolExecutor(max_workers=16) as ex:
        fs={ex.submit(m.parse_day,d):d for d in days}
        for f in as_completed(fs):
            recs.append(f.result())
    rows=[r for x in recs if x['status']=='PASS' for r in x['rows']]
    d=pd.DataFrame(rows)
    if d.empty: return d,recs
    d=d.sort_values(['date','asset']).reset_index(drop=True)
    out=[]; idx=pd.Index(sorted(days),name='date')
    for a in m.ASSETS:
        g=d[d.asset==a].set_index('date').reindex(idx); present=g['ticker'].notna(); g['asset']=a
        g['ret']=(g['close']/g['open']-1)*1e4
        for col in ('trade_count','volume','oi'):
            delta=g[col].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_'+col]=delta; g['z_'+col]=delta/scale.replace(0,np.nan)
        g['avg_size']=g['volume']/g['trade_count'].replace(0,np.nan); delta=g['avg_size'].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_avg_size']=delta; g['z_avg_size']=delta/scale.replace(0,np.nan)
        g['turnover']=g['volume']/g['oi'].replace(0,np.nan); delta=g['turnover'].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_turnover']=delta; g['z_turnover']=delta/scale.replace(0,np.nan)
        g['range_per_trade']=(g['high']-g['low'])/g['trade_count'].replace(0,np.nan); delta=g['range_per_trade'].diff(); scale=delta.abs().shift(1).rolling(20,min_periods=15).median(); g['d_range_per_trade']=delta; g['z_range_per_trade']=delta/scale.replace(0,np.nan)
        out.append(g[present].reset_index())
    return pd.concat(out,ignore_index=True),recs


def guarded_feature_map(d,sessions):
    ordered=sorted(sessions); piv={}
    for s in ordered:
        q=d[d.date==s]
        if len(q)==2: piv[s]={r.asset:r for _,r in q.iterrows()}
    mapp={}; hist=[]
    for i,s in enumerate(ordered):
        if i==0: continue
        prev=ordered[i-1]
        if prev not in piv: continue
        r=piv[prev]
        if set(r)!=set(m.ASSETS): continue
        zc={a:float(r[a].z_trade_count) for a in m.ASSETS}; za={a:float(r[a].z_avg_size) for a in m.ASSETS}
        rec={'prev':prev,'rows':r,'zc':zc,'za':za,'rel_count':zc['WIN']-zc['WDO'],'rel_avg':za['WIN']-za['WDO']}
        if len(hist)>=60:
            q=hist[-60:]; X=np.array([[x['zcW'],x['zcD'],x['relA']] for x in q],float); Y=np.array([x['retW'] for x in q],float); good=np.isfinite(X).all(1)&np.isfinite(Y)
            if good.sum()>=45:
                A=np.c_[np.ones(good.sum()),X[good]]; bt=np.linalg.lstsq(A,Y[good],rcond=None)[0]; rh=Y[good]-A@bt; sd=np.std(rh); x=np.array([zc['WIN'],zc['WDO'],rec['rel_avg']],float)
                if sd>0 and np.isfinite(x).all(): rec['resid_z']=(float(r['WIN'].ret)-np.r_[1.,x]@bt)/sd
        mapp[s]=rec
        hist.append({'zcW':zc['WIN'],'zcD':zc['WDO'],'relA':rec['rel_avg'],'retW':float(r['WIN'].ret)})
    return mapp


def main():
    m.daily_table=guarded_daily; m.feature_map=guarded_feature_map
    a=argparse.ArgumentParser(); a.add_argument('--out',required=True); a.add_argument('--ledger',required=True); a.add_argument('--cells',required=True); a.add_argument('--manifest',required=True); z=a.parse_args()
    m.main(z.out,z.ledger,z.cells,z.manifest)


if __name__=='__main__': main()
