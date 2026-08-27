# GATE BTC B3 Autonomous Science Protocol v2

Status: FROZEN_BEFORE_H420_ECONOMICS

Purpose: continue the autonomous B3 scientific factory across the v1 grammar boundary without using any H420+ economic result to construct later families.

## Boundary and inheritance

Protocol v1 remains immutable and authoritative for its original 256 ordered contracts. Therefore H170 through H425 retain exactly their v1 family definitions, including a rolling 20-prior-session median/MAD standardization.

Protocol v2 is frozen before any H420-H429 economics. The H420-H429 decade is allowed to cross the protocol boundary: H420-H425 consume the six remaining v1 contracts and H426-H429 consume the first four v2-extension contracts. No already-materialized family is renamed, retuned or replaced.

## Deterministic v2 extension

The v1 feature, direction, decision-window, threshold and holding-horizon universes are inherited unchanged:

- features, fixed order: `OPEN_RETURN`, `OPEN_RANGE`, `REALIZED_VOL`, `VOLUME_EARLY`, `BAR_IMBALANCE`, `CLOSE_LOCATION`, `BODY_RANGE`, `GAP_FROM_PRIOR_CLOSE`
- directions, fixed order: `CONTINUATION`, `REVERSION`
- decision windows, fixed order: 15, 30, 60, 90 minutes
- absolute z thresholds, fixed order: 0.75, 1.00, 1.25, 1.50
- holding horizons: 30, 60, 120 minutes

V1 uses standardization lookback 20 sessions. V2 appends the following new lookbacks in this exact fixed order:

`10, 30, 40, 60, 80, 120, 160, 200, 252` prior sessions.

For each new lookback, the complete Cartesian product is ordered exactly as v1: feature, direction, decision window, threshold. The global family sequence is therefore:

1. all 256 v1 contracts at lookback 20;
2. all 256 contracts at lookback 10;
3. all 256 contracts at lookback 30;
4. then 40, 60, 80, 120, 160, 200 and 252 in that order.

This produces 2,560 unique preregistered family contracts from H170 onward, exactly divisible into 256 decades of ten. The sequence is deterministic and independent of all observed economic outcomes. A contract identity includes feature, direction, decision window, absolute z threshold and standardization lookback, so the v2 extension cannot clone a v1 contract.

When this complete v2 universe is exhausted the system must again fail closed with `AUTONOMOUS_SCIENCE_GRAMMAR_EXHAUSTED`; no automatic scientific invention beyond this protocol is authorized.

## Causal standardization

For a family with `standardization_lookback_sessions=L`, the raw session feature is standardized using exactly the immediately prior L finite session feature values. Current-session data never enters its own reference distribution. The center is the median of those L values and the scale is `1.4826 * median(abs(x - median))`. Fewer than L finite prior observations or zero MAD produces no signal for that session. No forward fill, interpolation or synthetic backfill is allowed.

## Economics and replication

All economics, cost gates, split, execution timing and survivor selection remain exactly those in protocol v1:

- discovery sessions: 2022-2024;
- independent replication: 2020-2021;
- cutoff exclusive: 2026-08-10;
- reference cost 2 bp, stress cost 3 bp;
- one-extra-bar delayed entry gate;
- minimum trades, side stability, calendar-half stability and concentration gates unchanged;
- family survives with at least two qualified holding-horizon cells in discovery and independent replication;
- at most two survivors, selected by ascending family id only, never by performance rank.

## Loop semantics

A generation always contains exactly ten consecutive H families. The generator may cross the v1/v2 boundary inside one decade. It must persist the complete preregistration before evaluating any family in that decade. A no-survivor terminal automatically advances to the next decade. A survivor terminal stops automatic scientific continuation and routes only through the separately authorized prospective-shadow activation path.

## Safety

`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `ENGINE_FEED=false`, `H1_ECONOMICS_READ=false`.

Operational recovery may repair source, orchestration and persistence only. It may not reorder the grammar, change lookbacks, alter thresholds, modify economics gates, read H1 economics, synthesize data or select future contracts from observed performance.
