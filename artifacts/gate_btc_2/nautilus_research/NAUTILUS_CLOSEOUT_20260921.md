# NautilusTrader scientific closeout — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

## Standalone conclusion
NautilusTrader 2.0.0rc5 was independently installed and executed from an upstream-pinned source SHA (`d7f1959efa02e84d7fde3226dc88a88a69a142fd`). The event-driven backtest engine, order lifecycle, execution-algorithm surface, fill models and static latency model are operational in the isolated QRDS research lane.

## Tested candidate: TWAP execution slicing
Frozen signal: EMA10/EMA20 on internally aggregated 250-trade bars using bundled Binance ETHUSDT trade ticks. TWAP parameters were frozen at 10s horizon / 2.5s interval.

Across 0.1, 1.0 and 5.0 ETH, TWAP produced more fills and slightly worse realized PnL than immediate execution. The adverse delta increased in absolute USDT with order size. No parameter retuning was performed.

Disposition: **REJECT TWAP AS A MIGRATABLE BENEFIT CLAIM** for this formulation. Retain TWAP only as an execution mechanism that can be independently tested when a strategy requires slicing.

## Tested candidate: execution-realism stress harness
Frozen signal and trade size: EMA10/EMA20, 250-trade bars, 1 ETH market orders. Only execution assumptions changed.

Scenarios: baseline, 1ms latency, 100ms latency, 1s latency, deterministic one-tick adverse slippage, and 100ms + one-tick adverse slippage.

Baseline realized PnL: -11.13815174 USDT.
- 1ms latency delta: -0.12380426 USDT
- 100ms latency delta: -0.04287512 USDT
- 1s latency delta: -0.26727216 USDT
- one-tick adverse slippage delta: -0.49752626 USDT
- 100ms + one-tick adverse slippage delta: -0.49749826 USDT

The same 15 submitted signals were preserved in all scenarios. This demonstrates that execution assumptions measurably alter realized outcomes even when research logic is frozen.

Disposition: **MIGRATE THE METHODOLOGY, NOT THE NUMERIC THRESHOLDS.**

Proposed Factory role: an `execution_realism_stress` validation gate for compatible candidates/survivors once a Decision→Execution Contract exists. The gate should stress latency, slippage/fill assumptions, fees, liquidity/order size, sequencing and data granularity under preregistered scenario envelopes. NautilusTrader should remain an external execution-audit engine; it should not replace the Factory research engine or import external alpha claims.

## System disposition
**NautilusTrader: CONCLUDED / RETAIN AS EXECUTION-REALISM AUDITOR.**

What migrates: execution-realism stress methodology / audit gate.
What does not migrate: TWAP superiority claim, external alpha, exact latency values as universal thresholds, exact slippage values as universal thresholds, or Nautilus as the Factory core engine.
