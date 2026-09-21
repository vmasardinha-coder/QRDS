# AI Hedge Fund isolated discovery — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

Upstream: `virattt/ai-hedge-fund`  
Pinned SHA: `154a8b2f46dca0f40764d814e4e747b0ad71f4c4`  
Pinned package: `aihf==2.3.0`

## Research question
Determine whether AI Hedge Fund contributes reusable research methodology to GATE BTC 2.0 beyond Freqtrade, NautilusTrader and TradingAgents.

## Candidate contributions
1. Distinguish an unavailable/abstained model from an explicit neutral signal during ensemble blending.
2. Strategy-sleeve capital allocation followed by master risk on the netted book.
3. Same cycle path for historical simulation and prospective execution modes.
4. Full per-cycle receipts for signals, blends, risk clamps, orders and fills.

## Boundaries
- Do not import LLM persona performance or external claimed returns.
- Do not call real trading APIs.
- Do not use provider/API-dependent behavior as evidence unless explicitly executed.
- Factory remains untouched during isolated research.
- Any migratable result must be abstracted into a deterministic methodology and independently compared against current Factory semantics before intake.

## First falsifiable POC
Hold signal values and model weights fixed. Verify whether the upstream blend distinguishes:
- bullish + abstained second model,
- bullish + explicit neutral second model,
- all models abstained.
Then verify that hard risk limits can only shrink the proposed book after strategy views are netted.

This tests semantics and correctness, not alpha.
