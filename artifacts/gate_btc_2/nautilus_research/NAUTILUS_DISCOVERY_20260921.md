# NautilusTrader discovery — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

Pinned upstream repository: `nautechsystems/nautilus_trader`  
Pinned upstream develop SHA: `d7f1959efa02e84d7fde3226dc88a88a69a142fd`  
Pinned packaged engine for standalone smoke: `nautilus_trader==2.0.0rc5`

## Why this is materially different from Freqtrade

NautilusTrader is being evaluated primarily as an execution- and market-microstructure research engine rather than as a strategy-source repository. Its event-driven backtest exposes explicit order lifecycle, execution algorithms, order emulation, risk engine, matching/fill semantics, latency and multi-venue abstractions, with architecture intended to carry from backtest toward live execution.

## Candidate contributions to GATE BTC 2.0

1. **Execution-slicing policy** — test whether parent/child execution policies, beginning with TWAP, improve implementation shortfall, fill stability or tail risk for otherwise frozen signals.
2. **Execution-realism stress harness** — use alternative fill/bar/trade/latency assumptions to falsify survivors whose apparent edge depends on optimistic execution.
3. **Risk-state component** — investigate ACTIVE/HALTED/REDUCING trading-state semantics as a research-only risk overlay, never as alpha by itself.
4. **Order-lifecycle parity audit** — compare Factory/Freqtrade results with a fuller event-driven order lifecycle.
5. **Multi-instrument sequencing audit** — explicitly test invariance to unrelated instrument presence/order and track current upstream execution-sequencing caveats.

## First tangible POC

The first POC is deliberately not alpha mining. It must prove that a pinned Nautilus 2.x engine can run an actual deterministic event-driven backtest in our CI boundary, expose order/fill/position reports, and preserve `RESEARCH_ONLY` / `SHADOW_ONLY` isolation.

If that passes, the first scientific candidate is `execution_slicing_policy`: immediate market execution vs TWAP under identical signal timestamps, quantities, market data and cost assumptions.

## Scientific boundary

- External example performance is not alpha evidence.
- No Nautilus strategy/example is promoted automatically.
- No Factory modification in this research branch.
- Any migration later is hypothesis/component abstraction only, followed by independent Factory validation.
