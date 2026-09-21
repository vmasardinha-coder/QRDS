# River standalone preregistration — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true  
REAL_CAPITAL=0

## System

- upstream: `online-ml/river`
- release: `0.26.1`
- upstream commit: `64285b9dd6c606804753235fe992bcf25b9856ee`
- role under test: online learning + causal concept-drift detection

## Tangible question

Does an online model with a frozen ADWIN error-drift reset policy improve a strictly causal next-period prediction/trading replay versus the **same online model without drift resets**, on the same observations, features, costs and clock?

This is a standalone capability/hypothesis test. It is not a Factory family admission.

## Frozen data

- venue: OKX public market data via CCXT
- instrument: BTC/USDT spot
- timeframe: 1h
- target observations: latest 8,000 completed hourly bars available at execution time
- no authenticated exchange account
- no orders
- no backfill from QRDS runtime

The exact downloaded rows are hashed into the run artifact.

## Frozen causal geometry

At completed hourly bar `t`:

1. features use only closes through `t`;
2. model predicts the return from `open[t+1]` to `open[t+2]`;
3. signal is therefore fixed before the economic holding interval starts;
4. simulated entry is `open[t+1]` and simulated exit is `open[t+2]`;
5. only after `open[t+2]` is observed may the model see the realized target and learn from `(x_t, y_t)`;
6. the drift detector receives the absolute prediction error only after the target is realized.

No same-bar target leakage is permitted.

## Frozen features

Simple causal return/state features, chosen before outcome inspection:

- close return over 1 hour;
- close return over 3 hours;
- close return over 6 hours;
- close return over 12 hours;
- close return over 24 hours;
- rolling 24-hour realized volatility of 1h returns;
- current close/open intrabar return;
- current high/low range normalized by close.

No feature search or post-outcome feature deletion.

## Frozen learner

Both arms use exactly the same River pipeline:

`StandardScaler -> LinearRegression`

No hyperparameter search.

### Arm A — baseline

Continuous online learning for the entire replay. Never reset.

### Arm B — drift reset

Same learner plus River `ADWIN()` on the realized absolute prediction-error stream.

When ADWIN reports drift:

- record the timestamp;
- reset only the learner and ADWIN state;
- immediately learn the just-resolved `(x_t, y_t)` as the first observation of the new learner;
- do not change features, costs, target, or thresholds.

Default River ADWIN parameters are frozen. No delta search.

## Frozen economic mapping

For each model independently:

- predicted next open-to-open return `> 0` -> long for exactly one hourly interval;
- predicted return `<= 0` -> flat;
- no shorting;
- no leverage;
- notional starts at 10,000;
- full notional when long;
- commission/cost = 10 bps per side (20 bps round trip);
- no position overlap;
- no compounding ambiguity: equity compounds naturally through sequential one-period returns.

## Primary comparison

The drift-reset formulation is considered economically improved only if, on this frozen replay, it shows **both**:

1. lower MAE than the no-reset baseline; and
2. higher net final equity after identical costs.

Secondary diagnostics:

- RMSE;
- directional accuracy;
- net return;
- max drawdown;
- trade count;
- number/timestamps of detected drifts.

No retune is allowed if either primary condition fails.

## Interpretation

Possible dispositions:

- `FAMILY_CANDIDATE`: both primary conditions pass and the effect is large enough to justify independent QRDS revalidation;
- `COMPONENT`: drift detection is operationally useful but economic uplift is not proven;
- `HOLD`: ambiguous/low-power result;
- `REJECT_FROZEN_CONFIGURATION`: frozen drift-reset formulation fails the primary comparison.

A positive standalone result still cannot migrate directly. Any future Factory intake must independently freeze data, PIT semantics, costs, partitions and holdout before economics.
