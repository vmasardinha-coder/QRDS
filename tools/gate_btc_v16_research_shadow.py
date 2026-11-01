"""Independent historical-seed V16 research shadow. Never writes V16B1."""
from __future__ import annotations
import copy, hashlib, html, json, math
from datetime import date, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from tools import gate_btc_v16b_shadow_signal as frozen

SERIES="V16_RESEARCH_HISTORICAL_SEED_20261031"
ROOT="runtime/ledgers/v16_research_shadow_20261031"
FEATURES=list(frozen.FEATURES)
SAFETY=dict(research_only=True,shadow_only=True,not_approved=True,
            engine_feed=False,orders=0,real_capital=0,canonical_credit=0)

def encode(x):
    return (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+"\n").encode()
def digest(x):return hashlib.sha256(encode(x)).hexdigest()
def positive(x):
    x=float(x)
    if not math.isfinite(x) or x<=0:raise ValueError("nonpositive/nonfinite value")
    return x
def first_signal(day):
    d=date.fromisoformat(day)+timedelta(days=1)
    while d.weekday()!=3:d+=timedelta(days=1)
    return d.isoformat()
def immutable(path,data):
    path=Path(path)
    if path.exists():
        if path.read_bytes()!=data:raise ValueError("immutable conflict: "+str(path))
    else:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

def feature_panel(daily,dates,members):
    """Same frozen 18-feature arithmetic; membership provenance stays separate."""
    d=daily.copy();d["date"]=pd.to_datetime(d.date)
    if d.duplicated(["date","symbol"]).any():raise ValueError("duplicate daily bar")
    if not np.isfinite(d[["close","volume_usd"]]).all().all() or (d.close<=0).any() or (d.volume_usd<0).any():
        raise ValueError("invalid daily values")
    c=d.pivot(index="date",columns="symbol",values="close").sort_index()
    if "BTCUSDT" not in c:raise ValueError("BTC benchmark missing")
    c=c.reindex(pd.date_range(c.index.min(),c.index.max()))
    v=d.pivot(index="date",columns="symbol",values="volume_usd").reindex(c.index)
    r=np.log(c).diff();b=r.BTCUSDT;f={};betas={}
    for h in (7,14,30,60,90):f["mom"+str(h)]=c/c.shift(h)-1
    for h in (30,60):
        betas[h]=r.rolling(h,min_periods=h).cov(b).div(b.rolling(h,min_periods=h).var().replace(0,np.nan),axis=0)
        f["beta"+str(h)]=betas[h];f["corr"+str(h)]=r.rolling(h,min_periods=h).corr(b)
    residual=r-betas[60].shift(1).mul(b,axis=0)
    for h in (7,14,30,60,90):f["residmom"+str(h)]=np.expm1(residual.rolling(h,min_periods=h).sum())
    for h in (14,30,60):f["vol"+str(h)]=r.rolling(h,min_periods=h).std(ddof=1)*np.sqrt(365)
    f["logvol30"]=np.log1p(v.rolling(30,min_periods=30).median())
    rows=[]
    for day in dates:
        t=pd.Timestamp(day)
        for s in members:
            x={"signal_date":str(t.date()),"symbol":s}
            for name in FEATURES:
                x[name]=f[name].at[t,s] if t in f[name].index and s in f[name] else np.nan
            x["feature_ok"]=all(np.isfinite(x[n]) for n in FEATURES)
            a,z=t+pd.Timedelta(days=1),t+pd.Timedelta(days=8)
            x["fwd_ret"]=float(c.at[z,s]/c.at[a,s]-1) if s in c and a in c.index and z in c.index and pd.notna(c.at[z,s]) and pd.notna(c.at[a,s]) else np.nan
            rows.append(x)
    return pd.DataFrame(rows)

def rank(panel,signal_date,fit_date,closed_cycles):
    p=panel.copy()
    if p.duplicated(["signal_date","symbol"]).any():raise ValueError("duplicate feature row")
    p["signal_date"]=pd.to_datetime(p.signal_date)
    p["ok"]=p.feature_ok & (p.logvol30>=frozen.LIQ_FLOOR) & p[FEATURES].notna().all(axis=1)
    train=p[p.ok & p.fwd_ret.notna() & (p.signal_date+pd.Timedelta(days=8)<=pd.Timestamp(fit_date))].copy()
    groups=[]
    for _,g in train.groupby("signal_date"):
        if len(g)<20:continue
        lo,hi=g.fwd_ret.quantile(.1),g.fwd_ret.quantile(.9)
        g=g.copy();g["cls"]=1;g.loc[g.fwd_ret<=lo,"cls"]=0;g.loc[g.fwd_ret>=hi,"cls"]=2
        groups.append(g)
    if len(groups)<52:raise ValueError("fewer than52 qualified matured training weeks")
    tr=pd.concat(groups).sort_values(["signal_date","symbol"])
    model=HistGradientBoostingClassifier(learning_rate=.05,max_iter=100,max_depth=2,
        min_samples_leaf=50,l2_regularization=10.,random_state=frozen.RANDOM_STATE)
    model.fit(tr[FEATURES].to_numpy(),tr.cls.to_numpy())
    cur=p[p.ok & (p.signal_date==pd.Timestamp(signal_date))].copy()
    if len(cur)<20:raise ValueError("fewer than20 liquidity-qualified current assets")
    prob=model.predict_proba(cur[FEATURES].to_numpy());classes=list(model.classes_)
    cur["score"]=(prob[:,classes.index(2)] if 2 in classes else 0)-(prob[:,classes.index(0)] if 0 in classes else 0)
    desc=cur.sort_values(["score","symbol"],ascending=[False,True]);asc=cur.sort_values(["score","symbol"])
    returns=[float(x["unscaled_gross_return"]) for x in closed_cycles[-13:]]
    vol=float(np.std(returns,ddof=1)*np.sqrt(52)) if len(returns)==13 else None
    exposure=min(1.,.2/vol) if vol is not None and vol>1e-9 else 1.
    return dict(signal_date=signal_date,fit_date=fit_date,qualified_training_weeks=len(groups),
        training_rows=len(tr),training_hash=hashlib.sha256(tr.to_csv(index=False).encode()).hexdigest(),
        eligible_assets=len(cur),long_ranking=desc.symbol.tolist(),short_ranking=asc.symbol.tolist(),
        scores={str(r.symbol):float(r.score) for r in cur.itertuples()},exposure=exposure,
        trailing_vol_ann=vol,**SAFETY)

def initial_state():
    return dict(series=SERIES,nav=1.,positions={},last_cutoff=None,anchor_date=None,
        btc_anchor=None,observations=0,cumulative_cost=0.,cumulative_funding=0.,
        closed_cycles=[],peak_nav=1.,max_drawdown=0.,daily_returns=[],**SAFETY)

def rebalance(nav,old,weights,prices,rate=.0015):
    if sum(abs(float(w)) for w in weights.values())>1.+1e-12:raise ValueError("gross exposure above1")
    for k in set(old)|set(weights):positive(prices[k])
    equity=positive(nav)
    for _ in range(60):
        qty={k:float(w)*equity/positive(prices[k]) for k,w in weights.items()}
        cost=rate*sum(abs(qty.get(k,0)-old.get(k,0))*prices[k] for k in set(old)|set(qty))
        nxt=nav-cost
        if nxt<=0:raise ValueError("insolvent shadow")
        if abs(nxt-equity)<1e-14:break
        equity=nxt
    else:raise ValueError("cost equation did not converge")
    equity=nxt;qty={k:float(w)*equity/prices[k] for k,w in weights.items()}
    return equity,qty,cost

def mark(state,cutoff,prices,funding,plan=None):
    """Signed linear paper quantities; explicit modeled fills/costs, no orders."""
    s=copy.deepcopy(state);day=date.fromisoformat(cutoff)
    if s["last_cutoff"] is not None and cutoff<=s["last_cutoff"]:raise ValueError("duplicate/out-of-order close")
    if plan and plan["entry_date"]!=cutoff:raise ValueError("plan/entry date mismatch")
    before=s["nav"];pnl=0.
    for key,pos in s["positions"].items():
        price=positive(prices[key]);pnl+=pos["quantity"]*(price-pos["last_price"])
        pos["last_price"]=price
    if not math.isfinite(funding):raise ValueError("invalid funding")
    s["nav"]+=pnl+funding;s["cumulative_funding"]+=funding
    positive(s["nav"])
    expired=bool(s["positions"]) and cutoff==s["exit_date"]
    if s["positions"] and cutoff>s["exit_date"]:raise ValueError("mark past frozen exit")
    if plan and s["positions"] and not expired:raise ValueError("overlapping weekly book")
    if expired:
        g=sum(p["weight"]*(p["last_price"]/p["entry_price"]-1) for p in s["positions"].values())
        s["closed_cycles"].append(dict(entry_date=s["entry_date"],exit_date=cutoff,
            unscaled_gross_return=g/s["exposure"]))
    cost=0.
    if expired or plan:
        old={k:p["quantity"] for k,p in s["positions"].items()}
        weights=plan["weights"] if plan else {}
        s["nav"],qty,cost=rebalance(s["nav"],old,weights,prices)
        s["cumulative_cost"]+=cost
        s["positions"]={k:dict(quantity=q,weight=weights[k],entry_price=prices[k],
            last_price=prices[k]) for k,q in qty.items()}
        if plan:
            s.update(entry_date=cutoff,exit_date=plan["exit_date"],exposure=plan["exposure"])
    btc=positive(prices["B|BTCUSDT"])
    if s["anchor_date"] is None:
        if not plan:raise ValueError("no economic anchor before first entry")
        s["anchor_date"]=cutoff;s["btc_anchor"]=btc
        interval=0
    else:
        interval=(day-date.fromisoformat(s["last_cutoff"])).days
        if interval==1:s["observations"]+=1;s["daily_returns"].append(s["nav"]/before-1)
    s["last_cutoff"]=cutoff;s["peak_nav"]=max(s["peak_nav"],s["nav"])
    dd=s["nav"]/s["peak_nav"]-1;s["max_drawdown"]=min(s["max_drawdown"],dd)
    row=dict(cutoff=cutoff,nav=s["nav"],return_since_start=s["nav"]-1,
        interval_days=interval,eligible_daily_observation=interval==1,
        interval_return=s["nav"]/before-1,price_pnl=pnl,funding=funding,cost=cost,
        cumulative_cost=s["cumulative_cost"],cumulative_funding=s["cumulative_funding"],
        btc_return=btc/s["btc_anchor"]-1,drawdown=dd,
        excess_vs_btc_pp=(s["nav"]-btc/s["btc_anchor"])*100)
    return s,row

def load_events(root):
    p=Path(root)/"EVENTS.jsonl";events=[];prev=None
    if p.exists():
        for line in p.read_text().splitlines():
            e=json.loads(line);h=e.pop("event_sha256")
            if e["previous_sha256"]!=prev or digest(e)!=h:raise ValueError("broken economic hash chain")
            e["event_sha256"]=h;events.append(e);prev=h
    return events
def append_event(root,state,row,inputs):
    root=Path(root);events=load_events(root)
    e=dict(sequence=len(events)+1,previous_sha256=events[-1]["event_sha256"] if events else None,
           row=row,state_after=state,input_manifest=inputs)
    e["event_sha256"]=digest(e)
    with (root/"EVENTS.jsonl").open("a") as f:f.write(json.dumps(e,sort_keys=True,allow_nan=False)+"\n")
    return e

def render(root,status):
    root=Path(root);events=load_events(root);rows=[e["row"] for e in events]
    (root/"STATUS.json").write_bytes(encode(status))
    pd.DataFrame(rows).to_csv(root/"ECONOMICS.csv",index=False)
    paths=[]
    if rows:
        series=[[100*r["nav"] for r in rows],[100*(1+r["btc_return"]) for r in rows]]
        lo=min(min(x) for x in series);hi=max(max(x) for x in series);span=max(hi-lo,1)
        for vals,color,label in zip(series,["#58a6ff","#f6ad55"],["V16 paralelo","BTC"]):
            pts=" ".join(f"{30+820*i/max(len(vals)-1,1):.1f},{220-180*(v-lo)/span:.1f}" for i,v in enumerate(vals))
            paths.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="3"/><text x="35" y="{20+20*len(paths)}" fill="{color}">{label}</text>')
    note="Treinamento histórico com universo fixado na criação: viés de sobrevivência; sem crédito para V16B1. Preços públicos, custos e fills modelados; sem ordens."
    body=f'<h1>V16 — shadow paralelo</h1><p>{html.escape(note)}</p><pre>{html.escape(json.dumps(status,indent=2,ensure_ascii=False))}</pre>'
    body+='<svg viewBox="0 0 900 250" role="img" aria-label="NAV base100 V16 e BTC">'+''.join(paths)+'</svg>'
    (root/"REPORT.html").write_text('<!doctype html><meta charset="utf-8"><title>V16 shadow paralelo</title><style>body{background:#111827;color:#eee;font:16px system-ui;max-width:1100px;margin:30px auto}pre{white-space:pre-wrap}svg{width:100%;background:#1f2937}</style>'+body)
