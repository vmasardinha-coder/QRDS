# GATE BTC — Phase 2 Profit-Retention Protocol

Status: **PREDECLARED RESEARCH-ONLY PROTOCOL**  
Pinned Phase-1 evidence run: **31276127634 (#115)**

## Question

Holding the point-in-time QOS entry selections fixed, does a simple exit/holding overlay retain more of the selected altcoin sleeve's favorable excursion than the existing hold-to-next-month-boundary behavior?

This phase does **not** attempt to repair or optimize the Phase-1 selector. Entry signals, picks, regimes and historical universe are fixed inputs from the pinned Phase-1 artifact.

## Primary sample

- signal month must have PIT coverage >=95%;
- a complete next monthly signal boundary must exist;
- selected pick must have an exact close on the signal date and boundary date in the Phase-1 validated source cascade;
- the final incomplete forward month is excluded fail-closed;
- no current-survivor substitution.

## Predeclared policies

All exits use daily closes and the same signal-date close anchor.

1. `MONTH_END`: baseline; exit at the next monthly signal boundary.
2. `FIXED_7D`: first daily close on/after 7 calendar days.
3. `FIXED_14D`: first daily close on/after 14 calendar days.
4. `FIXED_21D`: first daily close on/after 21 calendar days.
5. `LOCK_25`: after unrealized gain first reaches +20%, exit when 25% of the best observed gain has been given back.
6. `LOCK_50`: after +20%, exit when 50% of the best observed gain has been given back.
7. `LOCK_75`: after +20%, exit when 75% of the best observed gain has been given back.

The profit locks are **not stop-losses**. Before +20% activation they do nothing. The giveback is a fraction of peak PROFIT, not a percentage drawdown from price.

No policy may hold beyond the next monthly boundary.

## Metrics

Primary metric:

- paired mean selected-alt-sleeve return delta versus `MONTH_END`, by signal month and strategy.

Predeclared uncertainty check:

- paired 10,000-replicate bootstrap across signal months;
- deterministic seed `20260808`;
- report 95% interval and bootstrap probability that the paired mean delta is positive.

Diagnostics (not optimization gates):

- MFE and MAE per selected trade;
- month-end giveback = MFE - month-end realized return;
- +20% hit rate;
- round-trip rate: MFE >= +20% but month-end return <= 0;
- signal-level mean, median, win rate, 10th and 90th percentiles;
- regime decomposition.

## Interpretation guard

This is an exploratory Phase-2 research layer. A policy is **not approved** merely because its in-sample mean is highest. Evidence is considered promising only if improvement is paired, broad across months/regimes, economically meaningful, and survives a later untouched holdout / prospective shadow validation.

No parameter is added after inspecting results in order to rescue performance. If a later protocol explores other activation or giveback values, it must be a separately versioned study.

Safety: research-only, shadow-only, engine feed false, entry selection unchanged, orders=0, capital=0.
