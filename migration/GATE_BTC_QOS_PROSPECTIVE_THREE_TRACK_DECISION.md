# GATE BTC — QOS prospective three-track decision

Status: **FROZEN RESEARCH-ONLY SIDECAR**  
Operational promotion: **FORBIDDEN**  
Orders: **0**  
Capital: **0**

## Why this exists

The definitive historical survivorship Phase 1 closed the historical question: after reconstructing a point-in-time universe at high coverage, the current QOS selector did not demonstrate incremental alpha versus the unfiltered PIT cohort. The historical CAGR of the current-universe V2A therefore cannot be used as proof that the selector itself adds alpha.

The correct next question is prospective. Once a signal-date universe is captured immutably before outcomes are known, future disappearance of a token cannot silently remove it from the experiment. This sidecar measures the selector and the PRL50 exit rule separately without feeding or changing the frozen V2A engine.

## Three arms

For each eligible month-end signal and separately for `QOS_Moderada` and `QOS_Ultra`:

1. `PIT_CONTROL` — equal-weight baseline monthly return of the exact eligible alt candidate set frozen from that V2A signal snapshot.
2. `QOS_CONTROL` — equal-weight baseline monthly return of the exact QOS alt picks frozen in the same snapshot.
3. `QOS_PRL50` — the same frozen QOS picks and entry, with the frozen `PRL50_POSITION` exit rule.

The comparisons are:

- selector contribution = `QOS_CONTROL - PIT_CONTROL`;
- exit-rule contribution = `QOS_PRL50 - QOS_CONTROL`;
- whole-package delta = `QOS_PRL50 - PIT_CONTROL`.

## Survivorship guard versus data-coverage diagnostic

`raw_coverage_ratio` is recorded at signal time but is **not** allowed to rewrite the contemporaneous candidate set after the fact. A low value is a data-quality/generalizability warning, not a reason to reconstruct the month later using survivors.

The selector comparison is stricter: every frozen PIT candidate must have a resolved monthly outcome. If even one candidate is unresolved, that asset remains in the denominator and the tool blocks `PIT_CONTROL`, selector alpha, and package delta. It never silently drops the missing candidate and never synthesizes a provisional terminal return.

The PRL50 comparison may still be measured when the broad selector comparison is blocked, but only if all frozen selected QOS paths are resolved. A missing selected path fails closed.

A separately validated explicit terminal-outcome policy is required before a confirmed economic death/delisting can be resolved mechanically. Until then, unresolved terminal outcomes block the affected inference rather than being guessed.

## Execution convention

- First eligible signal: `2026-08-31`.
- Entry: first validated daily close strictly after the signal.
- Baseline exit: first validated daily close strictly after the next calendar month-end boundary.
- PRL50 activation: +20% from entry on a confirmed daily close.
- PRL50 giveback: 50% of the maximum profit reached after activation.
- PRL50 execution: first validated daily close strictly after the trigger; same-bar trigger/exit is forbidden.
- Price source is frozen per symbol at the signal snapshot; mid-cycle source substitution is forbidden.
- Economic result is not evaluated until the cycle is complete.

## Current engineering validation (2026-08-09)

The sidecar unit tests cover:

- frozen contract and safety boundaries;
- three-arm mathematics;
- next-bar PRL50 execution;
- append-only duplicate rejection and hash chains for result and daily path evidence;
- source-substitution fail-closed;
- immutable calendar-day path capture with retrospective gap/backfill rejection;
- unresolved PIT candidate remains in the frozen denominator and keeps selector inference pending;
- missing selected QOS daily observations block PRL50 inference rather than being reconstructed later;
- daily orchestration captures month-end signals, appends untouched paths, overlaps adjacent monthly cycles safely, and publishes a result only after the cycle is complete.

Nine local tests pass. The current V2A snapshot (data as of 2026-08-09) was also used as a structural dry-run input. Its raw coverage is 62.6667%; the sidecar records this as `LOW_LT95`. A synthetic first-eligible signal-date dry run confirmed that the snapshot can be frozen prospectively without pretending that 62.6667% is broad-market coverage.

## Boundaries

This sidecar does not alter:

- V2A ranking, features, weights, regime logic, costs, lag or rebalance;
- the historical Phase 1 result;
- the historical PRL50 v1.1 result;
- Gateway, Delta, D50, LOCK25/50 or B3;
- `main` or any operational state.

`RESEARCH_ONLY=True`, `SHADOW_ONLY=True`, `NOT_APPROVED=True`, `orders=0`, `capital=0` remain mandatory.
