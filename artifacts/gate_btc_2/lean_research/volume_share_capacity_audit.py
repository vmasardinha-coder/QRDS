import json, time, statistics
from datetime import datetime, timezone
import ccxt

LEAN_SHA='985ef30ad3ac774218c5ac516b4cb0aa2655730f'
SYMBOLS=['BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT']
TIMEFRAME='1h'
TARGET_BARS=4000
CAPITALS=[10_000,100_000,1_000_000,10_000_000]
ORDER_FRAC=0.10
VOLUME_LIMIT=0.025
PRICE_IMPACT=0.10


def fetch(ex,symbol,total=TARGET_BARS):
    out=[]; since=ex.milliseconds()-total*3600_000
    while len(out)<total:
        batch=ex.fetch_ohlcv(symbol,TIMEFRAME,since=since,limit=min(300,total-len(out)))
        if not batch: break
        if out and batch[0][0] <= out[-1][0]:
            batch=[x for x in batch if x[0] > out[-1][0]]
        if not batch: break
        out.extend(batch); since=out[-1][0]+1
        if len(batch)<50: break
        time.sleep(ex.rateLimit/1000)
    return out[-total:]


def pct(xs,p):
    if not xs: return None
    xs=sorted(xs); k=(len(xs)-1)*p; lo=int(k); hi=min(lo+1,len(xs)-1); w=k-lo
    return xs[lo]*(1-w)+xs[hi]*w


def summarize(rows,capital):
    bps=[]; saturated=0; zero_vol=0
    notional=capital*ORDER_FRAC
    for r in rows:
        price=float(r[4]); bar_volume=float(r[5])
        if price<=0 or bar_volume<=0:
            zero_vol += 1
            continue
        qty=notional/price
        share=qty/bar_volume
        used=min(share,VOLUME_LIMIT)
        if share >= VOLUME_LIMIT: saturated += 1
        slip_pct=used*used*PRICE_IMPACT
        bps.append(slip_pct*10000)
    return {
        'capital_usd':capital,
        'order_notional_usd':notional,
        'n':len(bps),
        'slippage_bps_mean':statistics.mean(bps) if bps else None,
        'slippage_bps_p50':pct(bps,.50),
        'slippage_bps_p95':pct(bps,.95),
        'slippage_bps_p99':pct(bps,.99),
        'slippage_bps_max':max(bps) if bps else None,
        'volume_limit_saturation_rate':saturated/len(bps) if bps else None,
        'zero_volume_bars':zero_vol,
    }

ex=ccxt.okx({'enableRateLimit':True})
results={}
for s in SYMBOLS:
    rows=fetch(ex,s)
    results[s]={
        'bars':len(rows),
        'start':datetime.fromtimestamp(rows[0][0]/1000,timezone.utc).isoformat() if rows else None,
        'end':datetime.fromtimestamp(rows[-1][0]/1000,timezone.utc).isoformat() if rows else None,
        'capacity':[summarize(rows,c) for c in CAPITALS],
    }

report={
    'source_system':'QuantConnect LEAN',
    'upstream_sha':LEAN_SHA,
    'component':'VolumeShareSlippageModel',
    'research_only':True,
    'shadow_only':True,
    'factory_modified':False,
    'formula':'volume_share=min(order_qty/bar_volume, volume_limit); slippage_pct=volume_share^2*price_impact',
    'frozen':{
        'symbols':SYMBOLS,
        'timeframe':TIMEFRAME,
        'target_bars':TARGET_BARS,
        'capital_usd':CAPITALS,
        'order_fraction_of_capital':ORDER_FRAC,
        'volume_limit':VOLUME_LIMIT,
        'price_impact':PRICE_IMPACT,
    },
    'results':results,
    'limitations':[
        'uses hourly OKX reported trade volume as bar volume',
        'capacity stress only, not a complete order-book/queue replay',
        'LEAN default model caps volume share at 2.5%, so reported max impact is mechanically bounded',
        'does not claim alpha; evaluates execution-realism value only',
    ],
}
print(json.dumps(report,indent=2,sort_keys=True))
