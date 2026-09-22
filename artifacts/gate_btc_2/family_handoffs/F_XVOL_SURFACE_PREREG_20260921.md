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
- underlying reference: Deribit BTC index / expiry forward
- research boundary: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `REAL_CAPITAL_BRL=0`, `ORDERS=0`

## Scientific idea

The options surface may contain regime information orthogonal to spot-price-only families. The family is defined by **surface state**, not by the QuantLib engine itself.

The initial frozen feature geometry is:

1. `atm_iv_near`
   - median mark IV of options nearest to forward moneyness 1.00 within the nearest eligible expiry.
2. `atm_iv_far`
   - same definition for the next eligible farther expiry.
3. `term_slope`
   - `atm_iv_far - atm_iv_near`.
4. `put_25d_iv_near`
   - near-expiry put IV closest to Black-76 delta -0.25.
5. `call_25d_iv_near`
   - near-expiry call IV closest to Black-76 delta +0.25.
6. `risk_reversal_25d`
   - `call_25d_iv_near - put_25d_iv_near`.
7. `butterfly_25d`
   - `0.5 * (call_25d_iv_near + put_25d_iv_near) - atm_iv_near`.
8. `surface_dispersion_near`
   - robust cross-strike IV dispersion for the near expiry.

No price direction rule is frozen here. This is deliberately a **family**, not a single hypothesis.

## Eligibility gate for one surface snapshot

A snapshot is feature-eligible only if all hold:

- at least 2 distinct expiries after the observation time;
- nearest eligible expiry has at least 5 calls and 5 puts with finite positive mark IV and forward/strike inputs;
- farther expiry has enough observations to estimate ATM IV;
- nearest-expiry ATM candidate exists within absolute log-moneyness <= 0.075;
- 25-delta call and put candidates exist with absolute delta-distance <= 0.10 from target;
- no duplicate instrument identity;
- no non-finite emitted feature.

Otherwise the snapshot is `ABSTAIN / SURFACE_NOT_ELIGIBLE`; missing features are never silently neutralized.

## Delta convention

Use Black-76 delta on the expiry forward and the option mark IV published by Deribit. For calls, target `+0.25`; for puts, target `-0.25`. This convention is frozen for the family extractor and is not a tunable alpha parameter.

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
