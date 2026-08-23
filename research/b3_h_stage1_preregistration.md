# B3 H NextGen — Stage 1 preregistration

Date: 2026-08-23
Status: RESEARCH ONLY / ECONOMICS BLOCKED UNTIL REAL PRE-H1 M5 INPUT PASSES ADAPTER

## Isolation invariant

No H1 prospective economics may be read, parsed, inferred, summarized or used. All Stage 1 input timestamps must be strictly before 2026-08-10 America/Sao_Paulo. The H1 runtime/ledger is not an admissible input source.

## Input contract

Stage 1 accepts only 5-minute WIN structural bars after `tools/gate_btc_b3_h_stage1_adapter.py` passes. Price series must be either explicit real contracts with no back adjustment or a continuous Profit/Nelogica export explicitly declared `UNADJUSTED_REAL_CONTRACT_PRICES` with reviewed real-contract roll policy. Unknown or adjusted continuous futures are rejected.

## Execution convention

All candidate information is formed from completed bars. Entry is no earlier than the next 5-minute bar open. Exits are evaluated using predeclared holding horizons; no same-bar clairvoyance. Costs are evaluated as round-trip point deductions at 10, 20 and 30 WIN points. No candidate is promoted on gross results alone.

## H4 — opening time-series momentum

Economic thesis: directional flow present in the opening window may persist intraday.

Coarse grid only:
- opening lookback: 15, 30, 60 minutes from 09:00
- direction: sign(close at end of lookback / session open - 1)
- entry: next 5-minute open
- holding horizon: 30, 60, 120 minutes
- long and short both allowed

Reject H4 if positive net expectancy is isolated to one exact lookback/holding pair, one side, or one short calendar cluster.

## H2 — opening overreaction / mean reversion

Economic thesis: sufficiently large opening displacement may partially revert.

To avoid full-sample threshold fitting, the trigger scale is causal and trailing: prior-session daily true-range proxy built only from sessions strictly before the signal day. Fixed displacement multiples: 0.25, 0.50 and 0.75 of the trailing 20-session median session range.

Coarse grid:
- opening measurement window: 15, 30, 60 minutes
- trigger magnitude: 0.25, 0.50, 0.75 x trailing 20-session median range
- direction: opposite to opening displacement when trigger is met
- entry: next 5-minute open
- holding horizon: 30, 60, 120 minutes

Reject if results depend on one trigger bin, one year/half-year, one side, or a small event cluster.

## H3 — opening-range breakout / volatility expansion

Economic thesis: price leaving an established opening range can continue as volatility expands. This family carries the lowest prior and is deliberately easy to reject.

Coarse grid:
- opening range: first 15, 30, 60 minutes
- breakout confirmation: completed 5-minute close strictly beyond opening high/low
- first eligible breakout only per direction/session
- entry: next 5-minute open
- holding horizon: 30, 60, 120 minutes

Reject aggressively if next-bar execution or 20-point round-trip cost removes the effect, or if neighboring opening-range choices disagree materially.

## H5 — regime conditioning

H5 is not independently searched in Stage 1. It is eligible only after H2 or H4 survives unconditioned falsification. Any later regime variable must be causal, coarse, preregistered, and tested as a robustness question rather than a rescue filter.

## Required reports before prospective eligibility

For every tested family: gross and net expectancy, trade count, median trade, long/short split, calendar-half stability, concentration by best days, drawdown path, delayed-entry sensitivity, cost sensitivity, neighboring-parameter stability and day-cluster bootstrap uncertainty.

The research target is 0–2 survivors. A zero-survivor conclusion is valid. No prospective clock begins until a surviving rule set is frozen/versioned after these checks.

Safety: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `H1_ECONOMICS_READ=false`.
