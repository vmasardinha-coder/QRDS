# RESEARCH_ONLY=true
# SHADOW_ONLY=true
from __future__ import annotations

import json, re
from decimal import Decimal
from pathlib import Path

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.common import LogLevel
from nautilus_trader.config import BacktestEngineConfig, LoggerConfig, StrategyConfig
from nautilus_trader.execution import OneTickSlippageFillModel, StaticLatencyModel
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model import AccountType, Bar, BarType, Currency, InstrumentId, Money, OmsType, OrderSide, TraderId, Venue
from nautilus_trader.testkit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading import Strategy

OUT=Path('artifacts/gate_btc_2/nautilus_research/runtime_execution_stress'); OUT.mkdir(parents=True, exist_ok=True)
ETHUSDT=TestInstrumentProvider.ethusdt_binance(); TICKS=TestDataProvider.trades_from_binance_csv(ETHUSDT,'binance/ethusdt-trades.csv')
BAR_TYPE=BarType.from_str('ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL'); VENUE=Venue('BINANCE'); SIZE=Decimal('1.00')

class Cfg(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, **kwargs):
        super().__init__(**kwargs); self.instrument_id=instrument_id; self.bar_type=bar_type

class FrozenEMA(Strategy):
    def __init__(self,cfg:Cfg):
        super().__init__(cfg); self.fast=ExponentialMovingAverage(10); self.slow=ExponentialMovingAverage(20); self.signals=0
    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type,self.fast); self.register_indicator_for_bars(self.config.bar_type,self.slow); self.subscribe_bars(self.config.bar_type)
    def on_bar(self,_bar:Bar):
        if not self.indicators_initialized(): return
        want_long=self.fast.value>=self.slow.value
        if want_long and not self.portfolio.is_net_long(self.config.instrument_id):
            self.close_all_positions(self.config.instrument_id); self._submit(OrderSide.BUY)
        elif (not want_long) and not self.portfolio.is_net_short(self.config.instrument_id):
            self.close_all_positions(self.config.instrument_id); self._submit(OrderSide.SELL)
    def _submit(self,side):
        ins=self.cache.instrument(self.config.instrument_id)
        self.submit_order(self.order_factory.market(self.config.instrument_id,side,ins.make_qty(SIZE))); self.signals+=1
    def on_stop(self): self.close_all_positions(self.config.instrument_id)

def money_sum(series):
    total=0.0
    for x in series.astype(str):
        m=re.match(r'\s*([-+0-9.eE]+)',x)
        if m: total+=float(m.group(1))
    return total

def run_scenario(name, latency_ns=0, slip=False):
    eng=BacktestEngine(config=BacktestEngineConfig(trader_id=TraderId('BT-'+name.upper()),logging=LoggerConfig(stdout_level=LogLevel.ERROR)))
    kw={}
    if latency_ns: kw['latency_model']=StaticLatencyModel(base_latency_nanos=latency_ns)
    if slip: kw['fill_model']=OneTickSlippageFillModel(prob_fill_on_limit=1.0,prob_slippage=1.0,random_seed=42)
    eng.add_venue(venue=VENUE,oms_type=OmsType.NETTING,account_type=AccountType.CASH,base_currency=None,starting_balances=[Money(1_000_000.0,Currency.from_str('USDT')),Money(100.0,Currency.from_str('ETH'))],**kw)
    eng.add_instrument(ETHUSDT); eng.add_data(TICKS)
    s=FrozenEMA(Cfg(instrument_id=ETHUSDT.id,bar_type=BAR_TYPE)); eng.add_strategy(s); eng.run()
    fills=eng.generate_order_fills_report(); pos=eng.generate_positions_report()
    pnl=money_sum(pos['realized_pnl']) if 'realized_pnl' in pos.columns else float('nan')
    ret=float(pos['realized_return'].astype(float).sum()) if 'realized_return' in pos.columns else float('nan')
    out={'name':name,'latency_ns':latency_ns,'one_tick_slippage':slip,'signals':s.signals,'fills':int(len(fills)),'positions':int(len(pos)),'realized_pnl_usdt':pnl,'realized_return_sum':ret}
    fills.to_csv(OUT/f'{name}_fills.csv'); pos.to_csv(OUT/f'{name}_positions.csv'); eng.dispose(); return out

specs=[('baseline',0,False),('latency_1ms',1_000_000,False),('latency_100ms',100_000_000,False),('latency_1s',1_000_000_000,False),('slip_1tick',0,True),('latency100ms_slip1tick',100_000_000,True)]
rows=[run_scenario(*x) for x in specs]; base=rows[0]
for r in rows:
    r['delta_pnl_vs_baseline']=r['realized_pnl_usdt']-base['realized_pnl_usdt']; r['delta_return_vs_baseline']=r['realized_return_sum']-base['realized_return_sum']
assert all(r['signals']==base['signals'] for r in rows)
worst=min(rows,key=lambda r:r['realized_pnl_usdt'])
result={'research_only':True,'shadow_only':True,'factory_modified':False,'engine':'NautilusTrader 2.0.0rc5','upstream_sha':'d7f1959efa02e84d7fde3226dc88a88a69a142fd','signal':'frozen EMA10/EMA20, 250-tick internal bars, 1 ETH market orders','rows':rows,'worst_case':worst['name'],'worst_case_delta_pnl_usdt':worst['delta_pnl_vs_baseline'],'execution_fragility_metric':'worst_case_delta_pnl_vs_baseline','migratable_claim':'execution-realism stress harness methodology, not any particular latency/slippage threshold'}
(OUT/'execution_stress_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)); print(json.dumps(result,indent=2,sort_keys=True))
