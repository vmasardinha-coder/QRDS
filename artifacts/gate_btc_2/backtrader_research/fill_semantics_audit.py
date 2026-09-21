import csv, json, math, os, tempfile, time
from datetime import datetime, timezone
import ccxt
import backtrader as bt

UPSTREAM_SHA='b853d7c90b6721476eb5a5ea3135224e33db1f14'
SYMBOL='BTC/USDT'
TIMEFRAME='1h'
TARGET_BARS=4000
START_CASH=10000.0
COMMISSION=0.001
FAST=20
SLOW=50
SIZE_FRAC=0.95


def fetch(ex,total=TARGET_BARS):
    out=[]; since=ex.milliseconds()-total*3600_000
    while len(out)<total:
        batch=ex.fetch_ohlcv(SYMBOL,TIMEFRAME,since=since,limit=min(300,total-len(out)))
        if not batch: break
        if out and batch[0][0] <= out[-1][0]:
            batch=[x for x in batch if x[0] > out[-1][0]]
        if not batch: break
        out.extend(batch); since=out[-1][0]+1
        if len(batch)<50: break
        time.sleep(ex.rateLimit/1000)
    return out[-total:]


def ema(vals,n):
    a=2/(n+1); out=[]; e=None
    for v in vals:
        e=v if e is None else a*v+(1-a)*e
        out.append(e)
    return out


def custom(rows, next_open):
    closes=[float(r[4]) for r in rows]
    opens=[float(r[1]) for r in rows]
    ef=ema(closes,FAST); es=ema(closes,SLOW)
    cash=START_CASH; qty=0.0; trades=0; eq=[]
    pending=None
    for i in range(1,len(rows)):
        if pending is not None:
            action=pending; pending=None
            price=opens[i]
            if action=='buy' and qty==0:
                spend=cash*SIZE_FRAC
                q=spend/(price*(1+COMMISSION))
                fee=q*price*COMMISSION
                cash-=q*price+fee; qty+=q; trades+=1
            elif action=='sell' and qty>0:
                gross=qty*price; fee=gross*COMMISSION
                cash+=gross-fee; qty=0.0; trades+=1
        cross_up=ef[i]>es[i] and ef[i-1]<=es[i-1]
        cross_dn=ef[i]<es[i] and ef[i-1]>=es[i-1]
        if next_open:
            if cross_up and qty==0 and pending is None and i+1<len(rows): pending='buy'
            elif cross_dn and qty>0 and pending is None and i+1<len(rows): pending='sell'
        else:
            price=closes[i]
            if cross_up and qty==0:
                spend=cash*SIZE_FRAC
                q=spend/(price*(1+COMMISSION)); fee=q*price*COMMISSION
                cash-=q*price+fee; qty+=q; trades+=1
            elif cross_dn and qty>0:
                gross=qty*price; fee=gross*COMMISSION
                cash+=gross-fee; qty=0.0; trades+=1
        eq.append(cash+qty*closes[i])
    final=cash+qty*closes[-1]
    peak=-1e99; mdd=0.0
    for x in eq:
        peak=max(peak,x); mdd=min(mdd,x/peak-1 if peak>0 else 0)
    return {'final_value':final,'return':final/START_CASH-1,'max_drawdown':mdd,'order_fills':trades}


class EmaCross(bt.Strategy):
    params=dict(fast=FAST,slow=SLOW,size_frac=SIZE_FRAC)
    def __init__(self):
        self.ef=bt.ind.EMA(self.data.close,period=self.p.fast)
        self.es=bt.ind.EMA(self.data.close,period=self.p.slow)
        self.cross=bt.ind.CrossOver(self.ef,self.es)
        self.pending=None
        self.fills=0
        self.values=[]
    def notify_order(self, order):
        if order.status == order.Completed:
            self.fills += 1
        if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
            self.pending=None
    def next(self):
        self.values.append(self.broker.getvalue())
        if self.pending: return
        if not self.position and self.cross[0] > 0:
            cash=self.broker.getcash(); price=self.data.close[0]
            size=(cash*self.p.size_frac)/(price*(1+COMMISSION))
            self.pending=self.buy(size=size)
        elif self.position and self.cross[0] < 0:
            self.pending=self.close()


def backtrader_run(rows):
    fd,path=tempfile.mkstemp(suffix='.csv'); os.close(fd)
    try:
        with open(path,'w',newline='') as f:
            w=csv.writer(f)
            for r in rows:
                dt=datetime.fromtimestamp(r[0]/1000,timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                w.writerow([dt,r[1],r[2],r[3],r[4],r[5],0])
        cerebro=bt.Cerebro(stdstats=False)
        data=bt.feeds.GenericCSVData(dataname=path,dtformat='%Y-%m-%d %H:%M:%S',datetime=0,open=1,high=2,low=3,close=4,volume=5,openinterest=6,timeframe=bt.TimeFrame.Minutes,compression=60,headers=False)
        cerebro.adddata(data); cerebro.addstrategy(EmaCross)
        cerebro.broker.setcash(START_CASH); cerebro.broker.setcommission(commission=COMMISSION)
        strat=cerebro.run()[0]
        vals=strat.values
        peak=-1e99; mdd=0.0
        for x in vals:
            peak=max(peak,x); mdd=min(mdd,x/peak-1 if peak>0 else 0)
        final=cerebro.broker.getvalue()
        return {'final_value':final,'return':final/START_CASH-1,'max_drawdown':mdd,'order_fills':strat.fills}
    finally:
        try: os.unlink(path)
        except OSError: pass

ex=ccxt.okx({'enableRateLimit':True})
rows=fetch(ex)
same_close=custom(rows,False)
next_open=custom(rows,True)
bt_result=backtrader_run(rows)
report={
    'source_system':'Backtrader','upstream_sha':UPSTREAM_SHA,
    'research_only':True,'shadow_only':True,'factory_modified':False,
    'hypothesis':'execution_timing_semantics_audit',
    'data':{'symbol':SYMBOL,'timeframe':TIMEFRAME,'bars':len(rows),'start':datetime.fromtimestamp(rows[0][0]/1000,timezone.utc).isoformat(),'end':datetime.fromtimestamp(rows[-1][0]/1000,timezone.utc).isoformat()},
    'frozen':{'ema_fast':FAST,'ema_slow':SLOW,'start_cash':START_CASH,'commission_per_side':COMMISSION,'size_frac':SIZE_FRAC},
    'results':{'hypothetical_same_close':same_close,'causal_next_open_custom':next_open,'backtrader_market_order_default':bt_result},
    'deltas':{
        'next_open_minus_same_close_return_pp':(next_open['return']-same_close['return'])*100,
        'backtrader_minus_same_close_return_pp':(bt_result['return']-same_close['return'])*100,
        'backtrader_minus_custom_next_open_return_pp':(bt_result['return']-next_open['return'])*100,
    },
    'interpretation_guard':'Backtrader default market orders are submitted from a completed-bar signal and fill on a later bar; same-close result is intentionally hypothetical and used only to measure semantic optimism.',
}
print(json.dumps(report,indent=2,sort_keys=True))
