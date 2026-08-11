#!/usr/bin/env python3
"""Deterministic V16B prospective/shadow signal engine.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. No orders, no capital.

Input panel contract: one row per (signal_date,symbol), with the frozen 18
features, feature_ok, and fwd_ret for fully realized historical weeks. The
current signal may have fwd_ret missing. Shortability input is a causal
Friday-entry ledger; no current exchangeInfo is used for historical backfill.
"""
from __future__ import annotations
import argparse, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

CANDIDATE_ID='GATE_BTC_V16B_CAUSAL_SHORT_LIQ10_VOL20_FREEZE_20260811'
FEATURES=[
'mom7','mom14','mom30','mom60','mom90','residmom7','residmom14','residmom30','residmom60','residmom90',
'vol14','vol30','vol60','corr30','corr60','beta30','beta60','logvol30']
LIQ_FLOOR=np.log(10_000_000.0)
RANDOM_STATE=20260811

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def load_panel(path:Path)->pd.DataFrame:
    p=pd.read_pickle(path) if path.suffix.lower() in {'.pkl','.pickle'} else pd.read_csv(path)
    req={'signal_date','symbol','feature_ok','fwd_ret',*FEATURES}
    miss=req-set(p.columns)
    if miss: raise ValueError(f'missing panel columns: {sorted(miss)}')
    p['signal_date']=pd.to_datetime(p['signal_date'])
    p['feature_ok']=p['feature_ok'].astype(str).str.lower().isin(['true','1','yes']) if p['feature_ok'].dtype==object else p['feature_ok'].astype(bool)
    p['liq_ok_10m']=p['logvol30']>=LIQ_FLOOR
    p['v16_ok']=p['feature_ok'] & p['liq_ok_10m'] & p[FEATURES].notna().all(axis=1)
    p['extreme_cls_liq']=np.nan
    hist=p[p['v16_ok'] & p['fwd_ret'].notna()]
    for d,idx in hist.groupby('signal_date').groups.items():
        vals=p.loc[idx,'fwd_ret']
        if len(vals)<20: continue
        q10,q90=vals.quantile(.10),vals.quantile(.90)
        cls=np.ones(len(vals),dtype=int)
        cls[vals.to_numpy()<=q10]=0; cls[vals.to_numpy()>=q90]=2
        p.loc[idx,'extreme_cls_liq']=cls
    return p

def score_through(panel:pd.DataFrame, asof:pd.Timestamp)->pd.DataFrame:
    p=panel.copy(); p['v16_score']=np.nan
    dates=sorted(d for d in p.signal_date.unique() if pd.Timestamp(d)<=asof)
    clf=None; last_fit_i=None
    for i,d64 in enumerate(dates):
        d=pd.Timestamp(d64)
        past_dates=[pd.Timestamp(x) for x in dates[:i] if pd.Timestamp(x)+pd.Timedelta(days=8)<=d]
        if len(past_dates)<52: continue
        if clf is None or (i-last_fit_i)>=13:
            tr=p[p.signal_date.isin(past_dates) & p.v16_ok & p.extreme_cls_liq.notna()].dropna(subset=FEATURES)
            if tr.empty: raise RuntimeError(f'empty training set at {d.date()}')
            clf=HistGradientBoostingClassifier(learning_rate=.05,max_iter=100,max_depth=2,min_samples_leaf=50,
                                               l2_regularization=10.0,random_state=RANDOM_STATE)
            clf.fit(tr[FEATURES].to_numpy(),tr['extreme_cls_liq'].astype(int).to_numpy())
            last_fit_i=i
        idx=p.index[(p.signal_date==d)&p.v16_ok]
        if len(idx):
            pr=clf.predict_proba(p.loc[idx,FEATURES].to_numpy()); classes=list(clf.classes_)
            p0=pr[:,classes.index(0)] if 0 in classes else np.zeros(len(idx))
            p2=pr[:,classes.index(2)] if 2 in classes else np.zeros(len(idx))
            p.loc[idx,'v16_score']=p2-p0
    return p

def shortable_sets(path:Path)->dict[pd.Timestamp,set[str]]:
    s=pd.read_csv(path); req={'friday_utc','asset'}
    if req-set(s.columns): raise ValueError('shortability ledger missing friday_utc/asset')
    s['friday_utc']=pd.to_datetime(s['friday_utc'])
    return {pd.Timestamp(d):set(g.asset.astype(str)) for d,g in s.groupby('friday_utc')}

def realized_history(scored:pd.DataFrame, shortsets:dict, asof:pd.Timestamp, cost_bps:float=15.0, lookback:int=13):
    dates=sorted(d for d in scored.loc[scored.v16_score.notna(),'signal_date'].unique() if pd.Timestamp(d)<asof)
    prev={}; realized=[]
    for d64 in dates:
        d=pd.Timestamp(d64); entry=d+pd.Timedelta(days=1)
        if len(realized)>=lookback:
            rv=np.std([r['gross_unscaled'] for r in realized[-lookback:]],ddof=1)*np.sqrt(52)
            exposure=min(1.0,.20/rv) if rv>1e-9 else 1.0
        else: exposure=1.0
        g=scored[(scored.signal_date==d)&scored.v16_ok&scored.v16_score.notna()].copy()
        if len(g)<20: continue
        longs=g.sort_values('v16_score',ascending=False).head(10)
        pool=g[g.symbol.isin(shortsets.get(entry,set()))].sort_values('v16_score')
        if len(pool)<10: continue
        shorts=pool.head(10)
        if longs.fwd_ret.isna().any() or shorts.fwd_ret.isna().any(): continue
        weights={s:.05*exposure for s in longs.symbol}; weights.update({s:-.05*exposure for s in shorts.symbol})
        keys=set(prev)|set(weights); turnover=sum(abs(weights.get(k,0)-prev.get(k,0)) for k in keys)
        gross_un=.05*longs.fwd_ret.sum()-.05*shorts.fwd_ret.sum()
        realized.append({'signal_date':d,'gross_unscaled':gross_un,'exposure':exposure,'turnover':turnover})
        prev=weights
    return realized,prev

def generate(panel:pd.DataFrame, shortsets:dict, signal_date:pd.Timestamp):
    scored=score_through(panel,signal_date)
    hist,prev=realized_history(scored,shortsets,signal_date)
    if len(hist)>=13:
        rv=np.std([r['gross_unscaled'] for r in hist[-13:]],ddof=1)*np.sqrt(52)
        exposure=min(1.0,.20/rv) if rv>1e-9 else 1.0
    else: rv=np.nan; exposure=1.0
    entry=signal_date+pd.Timedelta(days=1)
    g=scored[(scored.signal_date==signal_date)&scored.v16_ok&scored.v16_score.notna()].copy()
    if len(g)<20: return {'status':'BLOCKED_N_LT20','candidate_id':CANDIDATE_ID,'signal_date':str(signal_date.date())}
    longs=g.sort_values('v16_score',ascending=False).head(10)
    pool=g[g.symbol.isin(shortsets.get(entry,set()))].sort_values('v16_score')
    if len(pool)<10: return {'status':'BLOCKED_SHORTABLE_LT10','candidate_id':CANDIDATE_ID,'signal_date':str(signal_date.date()),'shortable_n':len(pool)}
    shorts=pool.head(10)
    weights={s:.05*exposure for s in longs.symbol}; weights.update({s:-.05*exposure for s in shorts.symbol})
    keys=set(prev)|set(weights); turnover=sum(abs(weights.get(k,0)-prev.get(k,0)) for k in keys)
    return {
      'status':'PASS_SHADOW_SIGNAL','candidate_id':CANDIDATE_ID,
      'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ORDERS':0,'REAL_CAPITAL':0,
      'signal_date_utc':str(signal_date.date()),'entry_date_utc':str(entry.date()),
      'longs':longs[['symbol','v16_score']].to_dict('records'),'shorts':shorts[['symbol','v16_score']].to_dict('records'),
      'eligible_n':int(len(g)),'shortable_n':int(len(pool)),'exposure':float(exposure),
      'trailing_vol_ann':None if np.isnan(rv) else float(rv),'turnover_vs_prior':float(turnover),
      'cost_bps':15.0
    }

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--panel',required=True); ap.add_argument('--shortability',required=True); ap.add_argument('--signal-date',required=True); ap.add_argument('--output',required=True)
    a=ap.parse_args(); pp=Path(a.panel); sp=Path(a.shortability); out=Path(a.output); sd=pd.Timestamp(a.signal_date)
    panel=load_panel(pp); ss=shortable_sets(sp); result=generate(panel,ss,sd)
    result['panel_sha256']=sha256_file(pp); result['shortability_sha256']=sha256_file(sp)
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result,indent=2))
    return 0 if result['status'].startswith('PASS') else 2
if __name__=='__main__': raise SystemExit(main())
