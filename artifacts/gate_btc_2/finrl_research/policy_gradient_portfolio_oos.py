import json, math, time, random
from datetime import datetime, timezone

import ccxt
import numpy as np
import torch

UPSTREAM_SHA = '2334a5fe6d30629157f13c3b0319e1637e15e123'
SYMBOLS = ['BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT']
TIMEFRAME = '1h'
TARGET_BARS = 6000
TRAIN_FRAC = 0.70
ROUND_TRIP_COST = 0.002
SEEDS = [11, 29, 47, 71, 101]
EPOCHS = 120
LR = 0.01
HIDDEN = 16


def fetch(ex, symbol, total=TARGET_BARS):
    out=[]
    ms=3600_000
    since=ex.milliseconds()-total*ms
    while len(out)<total:
        batch=ex.fetch_ohlcv(symbol,TIMEFRAME,since=since,limit=min(300,total-len(out)))
        if not batch: break
        if out and batch[0][0] <= out[-1][0]:
            batch=[x for x in batch if x[0] > out[-1][0]]
        if not batch: break
        out.extend(batch)
        since=out[-1][0]+1
        if len(batch)<50: break
        time.sleep(ex.rateLimit/1000)
    return out[-total:]


def align(series):
    maps={s:{r[0]:r for r in rows} for s,rows in series.items()}
    common=sorted(set.intersection(*(set(m.keys()) for m in maps.values())))
    px=np.array([[maps[s][t][4] for s in SYMBOLS] for t in common],dtype=np.float64)
    return common,px


def build_features(px):
    lr=np.diff(np.log(px),axis=0)
    # At decision t, only returns through t-1 are used. Features become valid after 168h.
    feats=[]; future=[]; indices=[]
    for t in range(168, len(px)-1):
        hist=lr[:t]
        r24=hist[-24:].sum(axis=0)
        r168=hist[-168:].sum(axis=0)
        vol24=hist[-24:].std(axis=0)
        vol168=hist[-168:].std(axis=0)
        x=np.concatenate([r24,r168,vol24,vol168])
        y=px[t+1]/px[t]-1.0
        feats.append(x); future.append(y); indices.append(t)
    return np.asarray(feats,np.float32),np.asarray(future,np.float32),np.asarray(indices)


def softmax_np(z):
    z=z-np.max(z); e=np.exp(z); return e/e.sum()


def evaluate_weights(weights, future, cost=ROUND_TRIP_COST):
    # weights shape [T, 5], first column cash. Turnover cost uses half-L1 convention
    eq=1.0; peak=1.0; mdd=0.0; turnover=0.0; rets=[]
    prev=np.array([1.0,0,0,0,0],dtype=np.float64)
    for w,y in zip(weights,future):
        to=0.5*np.abs(w-prev).sum()
        gross=np.dot(w[1:],y)
        net=gross-cost*to
        eq*=max(1e-9,1.0+net)
        peak=max(peak,eq); mdd=min(mdd,eq/peak-1.0)
        turnover += to; rets.append(net)
        # drift risky weights after market move, cash unchanged
        vals=np.concatenate([[w[0]], w[1:]*(1.0+y)])
        prev=vals/vals.sum()
    arr=np.asarray(rets)
    mean=float(arr.mean()) if len(arr) else 0.0
    std=float(arr.std(ddof=1)) if len(arr)>1 else 0.0
    sharpe=(mean/std*math.sqrt(365*24)) if std>0 else None
    return {'return':eq-1.0,'max_drawdown':mdd,'turnover':turnover,'mean_hourly':mean,'sharpe_annualized':sharpe}


def baselines(x,future):
    n=len(x)
    ew=np.tile(np.array([0.0,.25,.25,.25,.25]),(n,1))
    mom=[]
    for row in x:
        r24=row[:4]
        scores=np.maximum(r24,0.0)
        if scores.sum()<=1e-12:
            w=np.array([1.0,0,0,0,0])
        else:
            risky=scores/scores.sum()
            w=np.concatenate([[0.0],risky])
        mom.append(w)
    return {'equal_weight':evaluate_weights(ew,future),'positive_24h_momentum':evaluate_weights(np.asarray(mom),future)}


class Policy(torch.nn.Module):
    def __init__(self, d):
        super().__init__()
        self.net=torch.nn.Sequential(torch.nn.Linear(d,HIDDEN),torch.nn.Tanh(),torch.nn.Linear(HIDDEN,5))
    def forward(self,x):
        return torch.softmax(self.net(x),dim=-1)


def train_and_eval(seed, xtr, ytr, xte, yte):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    mu=xtr.mean(axis=0); sd=xtr.std(axis=0); sd=np.where(sd<1e-6,1.0,sd)
    tx=torch.tensor((xtr-mu)/sd,dtype=torch.float32)
    ty=torch.tensor(ytr,dtype=torch.float32)
    model=Policy(tx.shape[1])
    opt=torch.optim.Adam(model.parameters(),lr=LR)
    for _ in range(EPOCHS):
        opt.zero_grad()
        w=model(tx)
        # causal sequence objective: mean log wealth with turnover penalty.
        risky=(w[:,1:]*ty).sum(dim=1)
        prev=torch.cat([torch.ones(1,1),torch.zeros(1,4)],dim=1)
        wprev=torch.cat([prev,w[:-1]],dim=0)
        turnover=.5*torch.abs(w-wprev).sum(dim=1)
        net=risky-ROUND_TRIP_COST*turnover
        loss=-torch.log(torch.clamp(1.0+net,min=1e-6)).mean()
        loss.backward(); opt.step()
    with torch.no_grad():
        wtr=model(tx).cpu().numpy()
        wte=model(torch.tensor((xte-mu)/sd,dtype=torch.float32)).cpu().numpy()
    return {'seed':seed,'train':evaluate_weights(wtr,ytr),'test':evaluate_weights(wte,yte),'avg_test_cash_weight':float(wte[:,0].mean()),'avg_test_weights':wte.mean(axis=0).tolist()}


ex=ccxt.okx({'enableRateLimit':True})
series={s:fetch(ex,s) for s in SYMBOLS}
times,px=align(series)
x,y,idx=build_features(px)
split=int(len(x)*TRAIN_FRAC)
xtr,ytr=x[:split],y[:split]
xte,yte=x[split:],y[split:]
runs=[train_and_eval(seed,xtr,ytr,xte,yte) for seed in SEEDS]
base_train=baselines(xtr,ytr); base_test=baselines(xte,yte)

rl_test_returns=[r['test']['return'] for r in runs]
rl_test_dd=[r['test']['max_drawdown'] for r in runs]
rl_test_sharpe=[r['test']['sharpe_annualized'] for r in runs if r['test']['sharpe_annualized'] is not None]
summary={
    'median_test_return':float(np.median(rl_test_returns)),
    'min_test_return':float(np.min(rl_test_returns)),
    'max_test_return':float(np.max(rl_test_returns)),
    'positive_test_seeds':int(sum(v>0 for v in rl_test_returns)),
    'median_test_max_drawdown':float(np.median(rl_test_dd)),
    'median_test_sharpe':float(np.median(rl_test_sharpe)) if rl_test_sharpe else None,
    'beats_equal_weight_return_seeds':int(sum(v>base_test['equal_weight']['return'] for v in rl_test_returns)),
    'beats_momentum_return_seeds':int(sum(v>base_test['positive_24h_momentum']['return'] for v in rl_test_returns)),
}
report={
    'source_system':'FinRL',
    'upstream_sha':UPSTREAM_SHA,
    'hypothesis':'policy_gradient_portfolio_allocation',
    'research_only':True,'shadow_only':True,'factory_modified':False,
    'causality':'features at decision t use returns ending at t-1; target return is t to t+1; scaler fitted on train only',
    'frozen':{'symbols':SYMBOLS,'timeframe':TIMEFRAME,'target_bars':TARGET_BARS,'train_frac':TRAIN_FRAC,'round_trip_cost':ROUND_TRIP_COST,'seeds':SEEDS,'epochs':EPOCHS,'lr':LR,'hidden':HIDDEN,'features':['24h_return','168h_return','24h_vol','168h_vol'],'cash_weight':True},
    'data':{'common_bars':len(times),'start':datetime.fromtimestamp(times[0]/1000,timezone.utc).isoformat(),'end':datetime.fromtimestamp(times[-1]/1000,timezone.utc).isoformat(),'samples':len(x),'train_samples':len(xtr),'test_samples':len(xte)},
    'baselines':{'train':base_train,'test':base_test},
    'rl_runs':runs,'rl_summary':summary,
    'limitations':['lightweight frozen direct policy-gradient abstraction inspired by FinRL PortfolioOptimizationEnv, not a claim of reproducing every FinRL implementation detail','single chronological split','OHLCV close-to-close portfolio simulation','generic turnover cost, no venue-specific slippage'],
}
print(json.dumps(report,indent=2,sort_keys=True))
