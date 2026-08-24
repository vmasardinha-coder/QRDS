#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math
from pathlib import Path

import numpy as np
import pandas as pd

import gate_btc_b3_h30_h39_cross_asset as b
import gate_btc_b3_h60_h69_data_probe as h60
import gate_btc_b3_h64_eia_wti as h64
import gate_btc_b3_h70_h79_data_probe as dq

FAMS=tuple(f'H{i}' for i in range(70,80))
ASSETS=('WIN','WDO')
HORIZONS=(60,120)
GEN='H70_H79_V1'


def std_move(x:pd.DataFrame, value:str, pct:bool=True, prefix:str='x'):
    d=x[['date',value]].copy().sort_values('date')
    d['move']=d[value].pct_change() if pct else d[value].diff()
    d['scale']=d['move'].abs().shift(1).rolling(20,min_periods=20).median()
    d['z']=d['move']/d['scale']
    return d.rename(columns={'move':f'{prefix}_move','z':f'{prefix}_z'})[['date',f'{prefix}_move',f'{prefix}_z']]


def prepare_sources():
    tm,t=dq.fetch_treasury_curve()
    t=t.sort_values('date').copy()
    t['slope_move']=t.slope.diff(); t['slope_scale']=t.slope_move.abs().shift(1).rolling(20,min_periods=20).median(); t['slope_z']=t.slope_move/t.slope_scale
    for col in ('us2y','us10y'):
        t[f'{col}_move']=t[col].diff(); t[f'{col}_scale']=t[f'{col}_move'].abs().shift(1).rolling(20,min_periods=20).median(); t[f'{col}_z']=t[f'{col}_move']/t[f'{col}_scale']
    t['slope_prev_move']=t.slope_move.shift(1)

    vm,v=dq.fetch_cboe('VIX'); v=v.sort_values('date').copy(); v['vix_move']=v.value.diff(); v['vix_scale']=v.vix_move.abs().shift(1).rolling(20,min_periods=20).median(); v['vix_z']=v.vix_move/v.vix_scale
    for q in (.2,.3,.7,.8): v[f'q{int(q*100)}']=v.value.shift(1).rolling(60,min_periods=60).quantile(q)
    v=v.rename(columns={'value':'vix_level'})
    v9m,v9=dq.fetch_cboe('VIX9D'); v9=v9.rename(columns={'value':'vix9d'})
    vr=v[['date','vix_level']].merge(v9[['date','vix9d']],on='date',how='inner').sort_values('date')
    vr['ratio']=vr.vix9d/vr.vix_level; vr['log_ratio']=np.log(vr.ratio); vr['lr_mean']=vr.log_ratio.shift(1).rolling(60,min_periods=60).mean(); vr['lr_std']=vr.log_ratio.shift(1).rolling(60,min_periods=60).std(ddof=0); vr['ratio_z']=(vr.log_ratio-vr.lr_mean)/vr.lr_std

    bm,brl=h60.fetch_bcb_brlusd(); brl=std_move(brl,'value',True,'brl')
    wm,wti=h64.fetch_eia(); wti=std_move(wti,'value',True,'wti')
    return {'treasury':t,'vix':v,'ratio':vr,'brl':brl,'wti':wti}, {'TREASURY_CURVE':tm,'VIX':vm,'VIX9D':v9m,'BRLUSD':bm,'WTI':wm}


def align(df:pd.DataFrame,sessions,cols):
    left=pd.DataFrame({'session':pd.to_datetime(sorted(sessions))}).sort_values('session'); d=df[['date']+list(cols)].sort_values('date')
    j=pd.merge_asof(left,d,left_on='session',right_on='date',direction='backward',allow_exact_matches=False); j['age_days']=(j.session-j.date).dt.days; j=j[(j.age_days>=1)&(j.age_days<=5)]
    return {r.session.date().isoformat():r for r in j.itertuples()}


def add(rows,fam,s,g,asset,side,h,param,bar,entry):
    exit_i=entry+h//bar; de=entry+1; dx=de+h//bar; col=f'open_{asset}'
    if side==0 or entry<0 or exit_i>=len(g): return
    gross=b.rb(int(side),float(g.iloc[entry][col]),float(g.iloc[exit_i][col])); delay=b.rb(int(side),float(g.iloc[de][col]),float(g.iloc[dx][col])) if dx<len(g) else np.nan
    if math.isfinite(gross): rows.append(dict(family=fam,session=s,asset=asset,side=int(side),param=param,horizon=int(h),gross=gross,delay=delay))


def own_first30(g,asset,bar):
    e=30//bar
    if e>=len(g): return 0
    a=float(g.iloc[0][f'open_{asset}']); z=float(g.iloc[e][f'open_{asset}'])
    return 1 if z>a else -1 if z<a else 0


def daily_win_return(g):
    a=float(g.iloc[0].open_WIN); z=float(g.iloc[-1].close_WIN)
    return (z/a-1)*10000 if a>0 and z>0 else np.nan


def generate(ss,bar,src):
    sessions=list(ss.keys()); T=align(src['treasury'],sessions,['slope_move','slope_z','slope_prev_move','us2y_move','us2y_z','us10y_move','us10y_z']); V=align(src['vix'],sessions,['vix_level','vix_move','vix_z','q20','q30','q70','q80']); VR=align(src['ratio'],sessions,['ratio','ratio_z']); B=align(src['brl'],sessions,['brl_move','brl_z']); W=align(src['wti'],sessions,['wti_move','wti_z'])
    rows=[]; disp_hist=[]; hist=[]; residual_hist={60:[],120:[]}
    for s in sorted(ss):
        g=ss[s]; tr=T.get(s); vx=V.get(s); rr=VR.get(s); br=B.get(s); wt=W.get(s)
        # H70 slope shock
        if tr and math.isfinite(getattr(tr,'slope_z',np.nan)) and math.isfinite(getattr(tr,'slope_move',np.nan)):
            sg=1 if tr.slope_move>0 else -1 if tr.slope_move<0 else 0
            for th in (1.0,1.5):
                if abs(tr.slope_z)>=th:
                    for asset in ASSETS:
                        for inv,name in ((1,'same'),(-1,'opposite')):
                            for h in HORIZONS: add(rows,'H70',s,g,asset,sg*inv,h,f'{name}_{th}',bar,0)
            # H71 persistence
            if math.isfinite(getattr(tr,'slope_prev_move',np.nan)) and tr.slope_prev_move*tr.slope_move>0:
                for th in (.75,1.0):
                    if abs(tr.slope_z)>=th:
                        for asset in ASSETS:
                            for inv,name in ((1,'continuation'),(-1,'reversal')):
                                for h in HORIZONS:add(rows,'H71',s,g,asset,sg*inv,h,f'{name}_{th}',bar,0)
            # H74 parallel/twist
            z2,z10=getattr(tr,'us2y_z',np.nan),getattr(tr,'us10y_z',np.nan); m2,m10=getattr(tr,'us2y_move',np.nan),getattr(tr,'us10y_move',np.nan)
            if all(math.isfinite(x) for x in (z2,z10,m2,m10)) and m2!=0 and m10!=0:
                state=f'{"2u" if m2>0 else "2d"}_{"10u" if m10>0 else "10d"}'; base=1 if m10>0 else -1
                for th in (.75,1.0):
                    if abs(z2)>=th and abs(z10)>=th:
                        for asset in ASSETS:
                            for inv,name in ((1,'same'),(-1,'inverse')):
                                for h in HORIZONS:add(rows,'H74',s,g,asset,base*inv,h,f'{state}|{name}|{th}',bar,0)
        # H72 VIX level conditioned first30
        if vx:
            level=getattr(vx,'vix_level',np.nan)
            for lo,hi,label in ((getattr(vx,'q20',np.nan),getattr(vx,'q80',np.nan),'20_80'),(getattr(vx,'q30',np.nan),getattr(vx,'q70',np.nan),'30_70')):
                regime='low' if math.isfinite(level) and math.isfinite(lo) and level<=lo else 'high' if math.isfinite(level) and math.isfinite(hi) and level>=hi else None
                if regime:
                    for asset in ASSETS:
                        sg=own_first30(g,asset,bar)
                        for inv,name in ((1,'continue'),(-1,'fade')):
                            for h in HORIZONS:add(rows,'H72',s,g,asset,sg*inv,h,f'{regime}|{label}|{name}',bar,30//bar)
        # H73 VIX term structure
        if rr:
            ratio,rz=getattr(rr,'ratio',np.nan),getattr(rr,'ratio_z',np.nan); states=[]
            if math.isfinite(ratio) and ratio<=.90:states.append(('ratio_low_0.90',1))
            if math.isfinite(ratio) and ratio>=1.10:states.append(('ratio_high_1.10',-1))
            if math.isfinite(rz):
                for th in (1.0,1.5):
                    if abs(rz)>=th: states.append((f'z_{"high" if rz>0 else "low"}_{th}',-1 if rz>0 else 1))
            for st,winbase in states:
                for asset in ASSETS:
                    base=winbase if asset=='WIN' else -winbase
                    for inv,name in ((1,'base'),(-1,'inverse')):
                        for h in HORIZONS:add(rows,'H73',s,g,asset,base*inv,h,f'{st}|{name}',bar,0)
        # H75/H76 joint states
        if tr and br and math.isfinite(getattr(tr,'slope_move',np.nan)) and math.isfinite(getattr(br,'brl_move',np.nan)) and tr.slope_move!=0 and br.brl_move!=0:
            state=f'{"fxu" if br.brl_move>0 else "fxd"}_{"su" if tr.slope_move>0 else "sd"}'; base=-1 if br.brl_move>0 else 1
            for asset in ASSETS:
                for inv,name in ((1,'same'),(-1,'inverse')):
                    for h in HORIZONS:add(rows,'H75',s,g,asset,base*inv,h,f'{state}|{name}',bar,0)
        if tr and wt and math.isfinite(getattr(tr,'slope_move',np.nan)) and math.isfinite(getattr(wt,'wti_move',np.nan)) and tr.slope_move!=0 and wt.wti_move!=0:
            state=f'{"wu" if wt.wti_move>0 else "wd"}_{"su" if tr.slope_move>0 else "sd"}'; base=1 if wt.wti_move>0 else -1
            for asset in ASSETS:
                for inv,name in ((1,'same'),(-1,'inverse')):
                    for h in HORIZONS:add(rows,'H76',s,g,asset,base*inv,h,f'{state}|{name}',bar,0)
        # H77/H78 shared non-equity vector
        vec=None
        if tr and vx and br and wt:
            raw=[-getattr(br,'brl_z',np.nan),-getattr(vx,'vix_z',np.nan),getattr(wt,'wti_z',np.nan),getattr(tr,'slope_z',np.nan)]
            if all(math.isfinite(x) for x in raw): vec=np.array(raw,dtype=float)
        if vec is not None:
            active=np.abs(vec)>=1.0; vote=int(np.sign(vec[active]).sum()) if active.any() else 0; breadth=int(active.sum())
            for need in (2,3):
                if breadth>=need and vote!=0:
                    sg=1 if vote>0 else -1
                    for asset in ASSETS:
                        base=sg if asset=='WIN' else -sg
                        for inv,name in ((1,'vote'),(-1,'inverse')):
                            for h in HORIZONS:add(rows,'H77',s,g,asset,base*inv,h,f'breadth{need}|{name}',bar,0)
            disp=float(np.std(vec,ddof=0)); scale=float(np.median(disp_hist[-60:])) if len(disp_hist)>=60 else np.nan
            if math.isfinite(scale) and scale>0:
                rel=disp/scale
                for th in (1.0,1.5):
                    if rel>=th:
                        for asset in ASSETS:
                            sg=own_first30(g,asset,bar)
                            for inv,name in ((1,'continue'),(-1,'fade')):
                                for h in HORIZONS:add(rows,'H78',s,g,asset,sg*inv,h,f'disp_{th}|{name}',bar,30//bar)
            disp_hist.append(disp)
        # H79 strictly causal lagged residual
        if len(hist)>=2:
            target=hist[-1]
            for win in (60,120):
                train=[r for r in hist[:-1] if np.isfinite(r['y']) and np.all(np.isfinite(r['x']))]
                if len(train)>=win and np.isfinite(target['y']) and np.all(np.isfinite(target['x'])):
                    trn=train[-win:]; X=np.array([r['x'] for r in trn],float); y=np.array([r['y'] for r in trn],float); X1=np.c_[np.ones(len(X)),X]
                    beta=np.linalg.lstsq(X1,y,rcond=None)[0]; pred=float(np.r_[1.0,np.array(target['x'],float)]@beta); resid=float(target['y']-pred)
                    rh=residual_hist[win]; scale=float(np.median(np.abs(rh[-20:]))) if len(rh)>=20 else np.nan
                    if math.isfinite(scale) and scale>0:
                        rz=resid/scale
                        for th in (1.5,2.0):
                            if abs(rz)>=th:
                                sg=own_first30(g,'WIN',bar)
                                for inv,name in ((1,'continuation'),(-1,'mean_reversion')):
                                    for h in HORIZONS:add(rows,'H79',s,g,'WIN',sg*inv,h,f'w{win}|z{th}|{name}',bar,30//bar)
                    rh.append(resid)
        # append current session to future H79 training only after all current signals
        if vec is not None:
            hist.append({'session':s,'x':vec.tolist(),'y':daily_win_return(g)})
    return pd.DataFrame(rows)


def summarize(t):
    out={}; cells=[]
    for fam in FAMS:
        ff=t[t.family==fam] if not t.empty else pd.DataFrame(); q=[]
        if not ff.empty:
            for (asset,param,h),g in ff.groupby(['asset','param','horizon']):
                ok,re,m=b.metric(g,*b.COST[asset]); cells.append(dict(family=fam,asset=asset,param=param,horizon=int(h),qualified=ok,reasons='|'.join(re),**m));
                if ok:q.append((asset,param,int(h)))
        legs=[]
        for asset in ASSETS:
            qa=[x for x in q if x[0]==asset]; ps={x[1] for x in qa}; hs={x[2] for x in qa}
            if len(qa)>=2 and (len(ps)>=2 or len(hs)>=2):legs.append(asset)
        out[fam]={'qualified_cells':len(q),'surviving_legs':legs,'survives':bool(legs),'qualified':sorted(f'{a}|{p}|{h}' for a,p,h in q)}
    return out,cells


def main(out,ledger,cells):
    src,meta=prepare_sources(); ds,dcov=b.sample(['2024_26'],5); rs,rcov=b.sample(['2020_22','2022_24'],15)
    D,dc=summarize(generate(ds,5,src)); R,rc=summarize(generate(rs,15,src)); cand=[f for f in FAMS if D[f]['survives']]; surv=[f for f in cand if R[f]['survives']][:2]
    states={f:('SURVIVOR_REPLICATED' if f in surv else 'REJECTED_FAILED_REPLICATION' if f in cand else 'REJECTED_DISCOVERY') for f in FAMS}
    p={'schema':'gate_btc.b3.h70_h79.economics.v1','generation':GEN,'status':'SURVIVORS_READY_FOR_SEPARATE_PROSPECTIVE' if surv else 'CLOSED_NO_H70_H79_SURVIVOR','cutoff_exclusive':'2026-08-10','states':states,'discovery':D,'replication':R,'survivors':surv,'sources':meta,'discovery_sync_sessions':len(ds),'replication_sync_sessions':len(rs),'discovery_median_common_bar_coverage':float(np.median(dcov)) if dcov else 0,'replication_median_common_bar_coverage':float(np.median(rcov)) if rcov else 0,'h1_economics_read':False,'survivor_partial_economics_read':False,'synthetic_backfill':False,'orders_generated':0,'real_capital_used':0,'engine_feed':False}
    Path(out).write_text(json.dumps(p,indent=2,sort_keys=True)+'\n');
    with Path(ledger).open('w') as fh:
        for fam in FAMS:fh.write(json.dumps({'family':fam,'generation':GEN,'state':states[fam],'discovery':D[fam],'replication':R[fam],'h1_economics_read':False,'survivor_partial_economics_read':False,'orders':0,'capital':0,'engine_feed':False},sort_keys=True)+'\n')
    pd.DataFrame([dict(sample='DISCOVERY',**x) for x in dc]+[dict(sample='REPLICATION',**x) for x in rc]).to_csv(cells,index=False)
    print(json.dumps(p,indent=2,sort_keys=True))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);a.add_argument('--ledger',required=True);a.add_argument('--cells',required=True);z=a.parse_args();main(z.out,z.ledger,z.cells)
