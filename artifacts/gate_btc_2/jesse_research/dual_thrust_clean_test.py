import json, time
from datetime import datetime, timezone
import ccxt

UP_LEN=21
DOWN_LEN=21
UP_COEFF=0.71
DOWN_COEFF=0.67
HOLD=24
ROUND_TRIP_COST=0.002
TOTAL_BARS=8000
SYMBOLS=['BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT']

def fetch(ex, symbol, total=TOTAL_BARS):
    out=[]
    since=ex.milliseconds()-total*3600_000
    while len(out)<total:
        batch=ex.fetch_ohlcv(symbol,'1h',since=since,limit=min(300,total-len(out)))
        if not batch: break
        if out and batch[0][0] <= out[-1][0]:
            batch=[x for x in batch if x[0] > out[-1][0]]
        if not batch: break
        out.extend(batch)
        since=out[-1][0]+1
        if len(batch)<50: break
        time.sleep(ex.rateLimit/1000)
    return out[-total:]

def test(rows):
    trades=[]; i=max(UP_LEN,DOWN_LEN)
    while i < len(rows)-HOLD:
        prev=rows[i-UP_LEN:i]
        lows=[r[3] for r in prev]; highs=[r[2] for r in prev]; closes=[r[4] for r in prev]
        rng_up=max(max(closes)-min(lows), max(highs)-min(closes))
        prevd=rows[i-DOWN_LEN:i]
        lows2=[r[3] for r in prevd]; highs2=[r[2] for r in prevd]; closes2=[r[4] for r in prevd]
        rng_dn=max(max(closes2)-min(lows2), max(highs2)-min(closes2))
        dt=datetime.fromtimestamp(rows[i][0]/1000,timezone.utc)
        day=dt.date(); j=i
        while j>0 and datetime.fromtimestamp(rows[j-1][0]/1000,timezone.utc).date()==day:
            j-=1
        day_open=rows[j][1]
        close=rows[i][4]
        up=day_open + UP_COEFF*rng_up
        dn=day_open - DOWN_COEFF*rng_dn
        side=1 if close>up else (-1 if close<dn else 0)
        if side:
            exitp=rows[i+HOLD][4]
            trades.append(side*(exitp/close-1)-ROUND_TRIP_COST)
            i += HOLD
        else:
            i += 1
    n=len(trades)
    if not n: return {'n':0}
    wins=sum(x>0 for x in trades)
    pos=sum(x for x in trades if x>0); neg=-sum(x for x in trades if x<0)
    eq=1.0; peak=1.0; mdd=0.0
    for x in trades:
        eq*=1+x; peak=max(peak,eq); mdd=min(mdd,eq/peak-1)
    return {'n':n,'mean_return':sum(trades)/n,'total_compounded':eq-1,'win_rate':wins/n,'profit_factor':(pos/neg if neg>0 else None),'max_drawdown':mdd}

ex=ccxt.okx({'enableRateLimit':True})
results={}
for s in SYMBOLS:
    rows=fetch(ex,s)
    cut=len(rows)//2
    results[s]={
        'bars':len(rows),
        'start':datetime.fromtimestamp(rows[0][0]/1000,timezone.utc).isoformat() if rows else None,
        'end':datetime.fromtimestamp(rows[-1][0]/1000,timezone.utc).isoformat() if rows else None,
        'full':test(rows),
        'first_half':test(rows[:cut]),
        'second_half':test(rows[cut:]),
    }
report={'research_only':True,'shadow_only':True,'factory_modified':False,'source_system':'jesse','jesse_core_sha':'432cce8a4b91828ce34dcaffac3f8e67354d061c','example_source':'Dual Thrust','implementation_note':'Clean causal abstraction; upstream example is not executed verbatim because down_max_high appears to reference the low column. No parameter retune after initial test.','frozen':{'up_len':UP_LEN,'down_len':DOWN_LEN,'up_coeff':UP_COEFF,'down_coeff':DOWN_COEFF,'hold_hours':HOLD,'round_trip_cost':ROUND_TRIP_COST,'target_bars':TOTAL_BARS},'results':results}
print(json.dumps(report,indent=2,sort_keys=True))
