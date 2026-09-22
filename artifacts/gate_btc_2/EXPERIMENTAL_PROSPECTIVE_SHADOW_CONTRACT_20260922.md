# GATE BTC 2.0 — Experimental prospective shadow contract

Frozen on 2026-09-22.

## Purpose

Create a legitimate middle state for hypotheses that are safe to observe forward but are not historically proven survivors.

This does **not** weaken survivor criteria. It only permits evidence accumulation under an explicitly zero-credit research status.

## Funnel

`IDEA -> HISTORICAL SCREEN -> EXPERIMENTAL_PROSPECTIVE_SHADOW -> CANDIDATE -> SURVIVOR -> EXECUTION`

Historical survivors may continue to use their existing route. Experimental shadow is not mandatory and cannot directly confer survivor status.

## Admission minimum

All must be true before D0:

1. mechanism frozen;
2. direction/position mapping frozen;
3. source identity valid;
4. source availability is causal prospectively;
5. causal execution rule defined;
6. cost/slippage model sufficient for shadow accounting;
7. no clean terminal rejection of the same hypothesis;
8. no post-result retune or sign flip;
9. D0 is the first observation after merged activation.

## Eligible classes

- `DATA_OR_SOURCE_BLOCKED_BUT_FORWARD_SOURCE_AVAILABLE`
- `INCONCLUSIVE_BUT_FORWARD_SAFE`
- `UNDERPOWERED_HISTORICAL_SCREEN`
- `NEAR_GATE_WITHOUT_CLEAN_TERMINAL_REJECTION`

## Explicitly ineligible

- same frozen hypothesis already cleanly rejected scientifically/economically;
- leakage, hindsight or invalid PIT;
- unresolved source/instrument identity;
- fabricated or backfilled prospective evidence;
- no causal execution rule;
- post-result parameter retune;
- post-result sign flip.

## Evidence semantics

- append-only;
- forward-only;
- duplicate credit = 0;
- late reconstruction credit = 0;
- missing observation => record gap, no credit;
- unavailable evidence stays explicitly unavailable and is never converted to neutral/zero.

## Promotion boundary

Experimental shadow carries:

- `NO_SURVIVOR_CREDIT`
- `NO_PROMOTION_AUTHORITY`
- `ZERO_RETROACTIVE_CREDIT`
- `FORWARD_EVIDENCE_ONLY`

It cannot jump directly to survivor or execution. Any transition to candidate requires a separate, preregistered forward adjudication contract. Any clean forward failure can be terminally tombstoned under that separate contract.

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `ENGINE_FEED=false`
- `ORDERS=0`
- `REAL_CAPITAL_BRL=0`
- `NO_BACKFILL=true`
- `NO_RETUNE=true`

## Item 2 boundary

This contract alone activates **zero families**. Item 3 will classify the existing base and decide which specific hypotheses are eligible to enter this lane.
