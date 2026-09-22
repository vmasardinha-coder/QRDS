# GATE BTC 2.0 — Factory Item 3 reclassification policy

This policy implements roadmap Item 3 against the frozen `EXPERIMENTAL_PROSPECTIVE_SHADOW` contract. It does not change survivor or promotion standards.

## Why the old terminal label is not sufficient

The historical Factory used terminal labels such as `SCIENTIFIC_REJECTION` for heterogeneous outcomes. Item 1 established that a clean terminal scientific rejection requires adequate evidence. Therefore Item 3 re-reads the actual cell evidence instead of trusting the queue label alone.

Examples:
- `NO_TRADES` is evidence insufficiency, not a clean economic rejection.
- `MIN_TRADES` is evidence insufficiency.
- `CALENDAR_HALF_STABILITY` is evidence insufficiency when fewer than two half-year buckets have at least 15 trades; otherwise it remains a hard robustness failure.
- `REFERENCE_COST_EDGE`, `STRESS_COST`, `DELAYED_ENTRY`, `SIDE_STABILITY`, and `CONCENTRATION` remain hard scientific/economic rejection reasons.

## Frozen family-level admission rule

A historical B3 autonomous family may enter the Item-2 experimental lane only when at least two of its three already-frozen horizon cells are either:
1. already qualified; or
2. fail solely because of evidence insufficiency as defined above.

This mirrors the original family semantics requiring at least two qualified horizons. No horizon, feature, sign, threshold, lookback, cost, session rule or holding period is selected or changed after seeing outcomes.

Any hard rejection still blocks rescue of that cell. The same cleanly rejected hypothesis is not resurrected.

## Scope

The canonical run must scan all 2,560 autonomous B3 families and use the latest legitimate requalification result when one exists. It also reports Grammar 007 and Grammar 008 dispositions so that clean historical rejects stay tombstoned and underspecified preregistrations stay invalid.

The old 512-family source-qualified V3 subset is included automatically. Its queue label is not accepted as proof by itself; the actual latest result cells are re-read.

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `ENGINE_FEED=false`
- `ORDERS=0`
- `REAL_CAPITAL=0`
- `NO_BACKFILL=true`
- `NO_RETUNE=true`
- experimental historical/retroactive credit = 0
- no direct promotion authority

The output is a reporting/classification artifact only. Activation of any eligible family requires a separate prospective source-binding and D0 contract after merge.
