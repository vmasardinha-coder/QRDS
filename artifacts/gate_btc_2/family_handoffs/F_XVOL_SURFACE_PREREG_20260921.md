# F-XVOL-SURFACE — preregistered family handoff

Date: 2026-09-21

## Purpose

Extract a reusable **options-implied volatility regime family** from the validated QuantLib + Deribit external capability without integrating QuantLib or Deribit as a second trading platform.

This artifact is a family definition / handoff only. It does not claim alpha, does not authorize Factory migration, and imports no winner parameters from any external backtest.

## Family identity

- family_id: `F-XVOL-SURFACE`
- class: `DERIVATIVES / IMPLIED_VOLATILITY_REGIME`
- origin: `QuantLib + Deribit options-pricing audit`
- source market: Deribit BTC European options
- underlying reference: Deribit expiry forward (`underlying_price`)
- research boundary: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `REAL_CAPITAL_BRL=0`, `ORDERS=0`

## Scientific idea

The options surface may contain regime information orthogonal to spot-price-only families. The family is defined by **surface state**, not by the QuantLib engine itself.

## Frozen feature geometry

For each expiry, define log-moneyness as `abs(log(K/F))`, where `K` is strike and `F` is that option's Deribit expiry forward.

1. `atm_iv_near`
   - among valid options in the nearest eligible expiry, find the minimum absolute log-moneyness;
   - take the median mark IV across instruments tied at that minimum (normally call/put at the same strike).
2. `atm_iv_far`
   - same rule for the next farther eligible expiry.
3. `term_slope`
   - `atm_iv_far - atm_iv_near`.
4. `put_25d_iv_near`
   - near-expiry put mark IV whose **undiscounted Black-76 forward delta** is closest to `-0.25`.
5. `call_25d_iv_near`
   - near-expiry call mark IV whose undiscounted Black-76 forward delta is closest to `+0.25`.
6. `risk_reversal_25d`
   - `call_25d_iv_near - put_25d_iv_near`.
7. `butterfly_25d`
   - `0.5 * (call_25d_iv_near + put_25d_iv_near) - atm_iv_near`.
8. `surface_dispersion_near`
   - interquartile range `Q75(mark_iv) - Q25(mark_iv)` across all valid options in the near expiry.

All IVs are expressed in **percentage points**, matching Deribit `mark_iv` units.

No price direction rule is frozen here. This is deliberately a **family**, not a single hypothesis.

## Black-76 forward delta convention

For `sigma = mark_iv / 100` and `T` in years:

`d1 = [ln(F/K) + 0.5*sigma^2*T] / [sigma*sqrt(T)]`

- call forward delta = `N(d1)`
- put forward delta = `N(d1) - 1`

This convention is frozen as feature geometry and is not a tunable alpha parameter.

## Expiry eligibility

An expiry is eligible only if:

- expiration is strictly after observation time;
- at least 5 valid calls and 5 valid puts exist;
- all used rows have finite positive strike, forward and mark IV;
- the ATM candidate has absolute log-moneyness <= `0.075`;
- the nearest call to +0.25 has absolute delta-distance <= `0.10`;
- the nearest put to -0.25 has absolute delta-distance <= `0.10`.

The family snapshot requires at least **two eligible expiries**. The earliest is `near`; the second earliest is `far`.

Instrument identity must be unique. Any duplicate identity or non-finite emitted feature makes the whole snapshot `ABSTAIN / SURFACE_NOT_ELIGIBLE`.

Missing features are never silently neutralized.

## What may vary later inside the Factory

Only after an admissible historical/prospective feature panel exists, the Factory may generate hypotheses from the **same frozen feature definitions**, for example:

- level regime: high/low `atm_iv_near`;
- term regime: contango/backwardation in IV via `term_slope`;
- skew regime: extreme `risk_reversal_25d`;
- convexity regime: extreme `butterfly_25d`;
- interaction with existing spot families as a gate, abstention layer, or independent family.

Thresholds/lookbacks/signs must be preregistered per child hypothesis or generated under the Factory's existing grammar/search discipline. They are not supplied by this handoff.

## Explicit prohibitions

- No historical alpha claim from the previous QuantLib pricing-consistency audit.
- No use of today's live surface as historical PIT evidence.
- No backfill presented as prospective evidence.
- No import of Deribit mark price reconstruction error as alpha.
- No arbitrary sign choice after observing returns.
- No Factory runtime, registry, order, capital, or engine mutation from this handoff.

## Required next evidence

Before economic adjudication, collect or obtain an admissible timestamped series of these features with explicit observation-time semantics. Then test child hypotheses under the common Factory economics and causal execution rules.

## Disposition

`F-XVOL-SURFACE = FAMILY_SPEC_READY / FEATURE_EXTRACTOR_REQUIRED / ECONOMIC_CLAIM_NOT_AUTHORIZED`
