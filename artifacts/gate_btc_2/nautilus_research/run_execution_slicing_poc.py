# RESEARCH_ONLY=true
# SHADOW_ONLY=true

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

from nautilus_trader.backtest import BacktestEngine
from nautilus_trader.common import LogLevel
from nautilus_trader.config import BacktestEngineConfig, ExecutionAlgorithmConfig, LoggerConfig, StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model import (
    AccountType,
    Bar,
    BarType,
    Currency,
    ExecAlgorithmId,
    InstrumentId,
    Money,
    OmsType,
    OrderSide,
    TraderId,
    Venue,
)
from nautilus_trader.testkit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading import Strategy

OUT = Path("artifacts/gate_btc_2/nautilus_research/runtime_execution_slicing")
OUT.mkdir(parents=True, exist_ok=True)
ETHUSDT = TestInstrumentProvider.ethusdt_binance()
TICKS = TestDataProvider.trades_from_binance_csv(ETHUSDT, "binance/ethusdt-trades.csv")
BAR_TYPE = BarType.from_str("ETHUSDT.BINANCE-250-TICK-LAST-INTERNAL")
BINANCE = Venue("BINANCE")
SIZES = [Decimal("0.10"), Decimal("1.00"), Decimal("5.00")]


class FrozenEmaConfig(StrategyConfig):
    def __init__(self, *, instrument_id: InstrumentId, bar_type: BarType, trade_size: Decimal, use_twap: bool, **kwargs):
        super().__init__(**kwargs)
        self.instrument_id = instrument_id
        self.bar_type = bar_type
        self.trade_size = trade_size
        self.use_twap = use_twap


class FrozenEmaExecutionStrategy(Strategy):
    def __init__(self, config: FrozenEmaConfig):
        super().__init__(config)
        self.fast = ExponentialMovingAverage(10)
        self.slow = ExponentialMovingAverage(20)
        self.twap_id = ExecAlgorithmId("TWAP")
        self.signal_count = 0

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast)
        self.register_indicator_for_bars(self.config.bar_type, self.slow)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, _bar: Bar):
        if not self.indicators_initialized():
            return
        if self.fast.value >= self.slow.value:
            if self.portfolio.is_net_flat(self.config.instrument_id):
                self._submit(OrderSide.BUY)
            elif self.portfolio.is_net_short(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self._submit(OrderSide.BUY)
        else:
            if self.portfolio.is_net_flat(self.config.instrument_id):
                self._submit(OrderSide.SELL)
            elif self.portfolio.is_net_long(self.config.instrument_id):
                self.close_all_positions(self.config.instrument_id)
                self._submit(OrderSide.SELL)

    def _submit(self, side: OrderSide):
        instrument = self.cache.instrument(self.config.instrument_id)
        kwargs = {}
        if self.config.use_twap:
            kwargs = {
                "exec_algorithm_id": self.twap_id,
                "exec_algorithm_params": {"horizon_secs": "10.0", "interval_secs": "2.5"},
            }
        self.submit_order(
            self.order_factory.market(
                self.config.instrument_id,
                side,
                instrument.make_qty(self.config.trade_size),
                **kwargs,
            )
        )
        self.signal_count += 1

    def on_stop(self):
        self.close_all_positions(self.config.instrument_id)


def money_sum(series) -> float:
    total = 0.0
    found = False
    for x in series.astype(str):
        m = re.match(r"\s*([-+0-9.eE]+)", x)
        if m:
            total += float(m.group(1))
            found = True
    return total if found else float("nan")


def run_one(size: Decimal, use_twap: bool):
    label = f"{'twap' if use_twap else 'immediate'}_{str(size).replace('.', 'p')}"
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            trader_id=TraderId(f"BT-{label.upper()}"),
            logging=LoggerConfig(stdout_level=LogLevel.ERROR),
        )
    )
    engine.add_venue(
        venue=BINANCE,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[Money(1_000_000.0, Currency.from_str("USDT")), Money(100.0, Currency.from_str("ETH"))],
    )
    engine.add_instrument(ETHUSDT)
    engine.add_data(TICKS)
    strategy = FrozenEmaExecutionStrategy(
        FrozenEmaConfig(instrument_id=ETHUSDT.id, bar_type=BAR_TYPE, trade_size=size, use_twap=use_twap)
    )
    engine.add_strategy(strategy)
    if use_twap:
        engine.add_native_exec_algorithm(
            "TwapAlgorithm",
            ExecutionAlgorithmConfig(exec_algorithm_id=ExecAlgorithmId("TWAP")),
        )
    engine.run()
    fills = engine.generate_order_fills_report()
    positions = engine.generate_positions_report()
    account = engine.generate_account_report(venue=BINANCE)
    fills.to_csv(OUT / f"{label}_fills.csv")
    positions.to_csv(OUT / f"{label}_positions.csv")
    account.to_csv(OUT / f"{label}_account.csv")
    realized_pnl = money_sum(positions["realized_pnl"]) if "realized_pnl" in positions.columns else float("nan")
    realized_return = float(positions["realized_return"].astype(float).sum()) if "realized_return" in positions.columns else float("nan")
    out = {
        "mode": "twap" if use_twap else "immediate",
        "trade_size_eth": float(size),
        "signals_submitted": strategy.signal_count,
        "fill_rows": int(len(fills)),
        "position_rows": int(len(positions)),
        "realized_pnl_usdt_sum": realized_pnl,
        "realized_return_sum": realized_return,
    }
    engine.dispose()
    return out


rows = []
for size in SIZES:
    immediate = run_one(size, False)
    twap = run_one(size, True)
    assert immediate["signals_submitted"] == twap["signals_submitted"]
    rows.append({
        "trade_size_eth": float(size),
        "immediate": immediate,
        "twap": twap,
        "delta_realized_pnl_usdt_twap_minus_immediate": twap["realized_pnl_usdt_sum"] - immediate["realized_pnl_usdt_sum"],
        "delta_realized_return_sum": twap["realized_return_sum"] - immediate["realized_return_sum"],
        "delta_fill_rows": twap["fill_rows"] - immediate["fill_rows"],
    })

result = {
    "research_only": True,
    "shadow_only": True,
    "factory_modified": False,
    "engine": "NautilusTrader 2.0.0rc5",
    "upstream_sha": "d7f1959efa02e84d7fde3226dc88a88a69a142fd",
    "data": "bundled Binance ETHUSDT trade ticks",
    "signal": "EMA10/EMA20 on 250-tick internal bars",
    "sizes_eth": [float(x) for x in SIZES],
    "twap": {"horizon_secs": 10.0, "interval_secs": 2.5},
    "rows": rows,
    "external_alpha_claim": False,
    "interpretation_rule": "TWAP is migratable only as a policy hypothesis if benefit is directionally stable as size increases; otherwise retain Nautilus as execution-audit tooling rather than exporting TWAP as a Factory hypothesis.",
}
(OUT / "execution_slicing_result.json").write_text(json.dumps(result, indent=2, sort_keys=True))
print(json.dumps(result, indent=2, sort_keys=True))
