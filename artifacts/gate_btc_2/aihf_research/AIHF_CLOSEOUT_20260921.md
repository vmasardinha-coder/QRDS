# AI Hedge Fund scientific closeout — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

Upstream: `virattt/ai-hedge-fund`  
Pinned SHA: `154a8b2f46dca0f40764d814e4e747b0ad71f4c4`  
Version: `2.3.0`

## Standalone conclusion
The pinned package installed successfully and the selected deterministic upstream portfolio/risk/backtest/event-study suite passed (`60 passed, 3 skipped`). The isolated structural POC also passed.

## What was proven
### 1. Abstention is not neutral
With equal model weights and the same bullish model signal:
- bullish + abstained contributor -> conviction `1.0`;
- bullish + explicit neutral contributor -> conviction `0.5`;
- all contributors abstained -> conviction `0.0`, portfolio weight `0.0`.

The semantic distinction is deterministic: an unavailable/abstained contributor is excluded from numerator and denominator, while an available zero is a real neutral vote.

### 2. Hard risk limits shrink the proposed netted book
For proposed weights `BTC=0.8, ETH=0.6, SOL=-0.4` (gross 1.8), a 0.5 position cap plus 0.9 gross cap produced final gross 0.9 and clamp receipts. Risk reduced exposures; it did not create additional exposure.

### 3. Market-neutral construction is deterministic
The frozen three-asset example produced gross 1.0 and net 0.0.

## What was not proven
- No alpha benefit was tested.
- No LLM/persona/provider behavior was used as evidence.
- No claimed upstream performance was imported.
- No external portfolio allocation or risk threshold is promoted as a Factory default.

## Duplicate audit
The current Factory has source/data availability and fail-closed materialization concepts, but no explicit canonical contract was found for contributor-level signal aggregation that distinguishes unavailable/abstained from an available neutral zero. The proposed migration is therefore a semantic integrity guard, not a duplicate alpha family.

Master-risk-after-netting is not migrated as a new concept in this closeout because it overlaps existing Factory risk/cost/governance infrastructure and was not shown to add independent predictive value.

## Disposition
**AI HEDGE FUND: STANDALONE VERIFIED / MIGRATE ONE INTEGRITY SEMANTIC.**

Migrate:
- `signal_availability_semantics`: unavailable/abstained contributors must not be coerced into neutral votes during aggregation; explicit neutral zero remains an available vote; all unavailable must fail closed to no active signal/zero weight; aggregation receipts preserve contributor availability and provenance.

Do not migrate:
- persona/LLM alpha claims;
- external performance;
- exact portfolio weights;
- exact risk thresholds;
- market-neutral parameters;
- AIHF as the Factory core engine.
