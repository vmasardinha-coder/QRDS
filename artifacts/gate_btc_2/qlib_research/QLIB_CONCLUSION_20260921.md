# Qlib standalone conclusion — 2026-09-21

## Classification

`CONCLUDED / RETAIN_AS_NONLINEAR_FACTOR_RESEARCH_SANDBOX`

Qlib is retained as an external supervised-ML / nonlinear-factor research sandbox and benchmarking component. The standalone capability is proven. No Qlib alpha, winner parameter, model performance, or upstream data claim is migrated into the Factory.

## Frozen system and evidence

- upstream: `microsoft/qlib`
- release: `v0.9.7`
- upstream SHA: `da920b7f954f48ab1bb64117c976710de198373e`
- experiment: `official_Alpha158_LightGBM_standalone`
- exact-head successful workflow run: `35647826511`
- artifact: `gate-btc-qlib-standalone`
- artifact id: `10661500973`
- artifact head SHA: `bfdb61fa9b77770270ee5d435b4a589d4083f055`
- config SHA256: `0cbe1f729f43a2b8cd735759e6244c2e9f8db967555bfe24a7143fce4605d680`
- data archive SHA256: `0e664a4bd60d126eefd92961e941f058763efe519995ad7573e50257fe5b4d20`

The final artifact reports `capability_pass=true` with all required evidence blocks present.

## Frozen benchmark

The test used the exact upstream Alpha158 + LightGBM benchmark configuration without tuning:

- market: CSI300
- benchmark: SH000300
- features: Alpha158
- model: `qlib.contrib.model.gbdt.LGBModel`
- train: 2008-01-01..2014-12-31
- validation: 2015-01-01..2016-12-31
- test/backtest: 2017-01-01..2020-08-01
- strategy: TopkDropoutStrategy
- topk: 50
- n_drop: 5
- open cost: 5 bps
- close cost: 15 bps
- minimum cost: 5
- account: 100,000,000

No hyperparameter search, alternate model, post-outcome date change, cost change, or strategy retune was allowed.

## Canonical standalone results

### Signal diagnostics

| Metric | Result |
|---|---:|
| IC | 0.0470620673 |
| ICIR | 0.3819740315 |
| Rank IC | 0.0487027118 |
| Rank ICIR | 0.4058043473 |

### Benchmark risk

| Metric | Result |
|---|---:|
| Annualized return | 11.3561% |
| Information ratio | 0.598699 |
| Max drawdown | -37.0479% |

### Excess return without cost

| Metric | Result |
|---|---:|
| Annualized return | 15.2322% |
| Information ratio | 1.793075 |
| Max drawdown | -7.6247% |

### Excess return with cost

| Metric | Result |
|---|---:|
| Annualized return | 11.5633% |
| Information ratio | 1.361538 |
| Max drawdown | -8.2156% |

The stored artifacts from the parser-repair sequence preserve the same frozen config/data hashes and the same economic blocks; the observed earlier red state was a result-parser failure, not an economic failure.

## What was proven

Qlib can provide a tangible end-to-end research workflow rather than only framework architecture:

1. high-dimensional Alpha158 feature generation;
2. supervised LightGBM forecast generation;
3. IC / Rank-IC diagnostics;
4. portfolio construction;
5. explicit transaction-cost accounting;
6. annualized return / IR / drawdown analysis;
7. sealed config and data provenance hashes;
8. reproducible artifact output suitable for independent auditing.

This is materially useful as a nonlinear-factor / ML research sandbox.

## What was NOT proven

The standalone economics are **not Factory-authoritative** because:

- the official Qlib prebuilt dataset was unavailable and the benchmark used the community-maintained Qlib-format China-stock archive;
- the domain is CSI300 equities, not BTC/B3;
- this data did not pass QRDS PIT/source/corporate-action governance;
- Qlib's external strategy/backtest result has not been independently reproduced on QRDS-governed data;
- Alpha158 and LightGBM were not independently admitted through Factory source/PIT/leakage/holdout gates.

Therefore the positive standalone result is evidence of platform capability, not evidence that the Factory should adopt Alpha158 or LightGBM.

## Integrated / QRDS confrontation decision

Status:

`BLOCKED_VALIDLY / QRDS_HISTORICAL_CROSS_SECTIONAL_PANEL_NOT_AVAILABLE`

This is a scientific boundary, not an implementation failure.

The existing QRDS V2A PIT lane is a 137-symbol cross-sectional universe, but its canonical contract is explicitly prospective:

- `latest_attempted_symbols = 137`;
- `prospective_point_in_time_universe_observed = true`;
- `future_point_in_time_only = true`;
- `retrospective_backfill_allowed = false`;
- historical credit = 0;
- prospective credit before D0 = 0.

That makes V2A appropriate for future prospective validation but not a historical train/validation/test panel for an Alpha158/LightGBM confrontation today.

Using BTC/ETH or another tiny universe merely to satisfy the word “integrated” would destroy the cross-sectional geometry of the frozen benchmark and would not be a meaningful comparison.

Accordingly, no forced integrated benchmark is run now.

## Ex-ante admission requirement for a future integrated test

A future Qlib-vs-QRDS confrontation may begin only after a QRDS-governed panel exists with:

1. multi-asset cross-sectional history of sufficient depth;
2. PIT universe membership by date;
3. immutable source identity and timestamps;
4. explicit delisting/corporate-action/missing-data semantics;
5. frozen chronological train / validation / holdout partitions before outcome inspection;
6. embargo where required;
7. fixed transaction-cost assumptions;
8. a simple frozen baseline plus the Qlib nonlinear model class;
9. identical data and scoring windows for both models;
10. no model/hyperparameter selection after holdout read.

V2A may eventually satisfy the prospective/OOS side after sufficient genuinely accumulated history, but its no-backfill contract must remain intact.

## Factory disposition

Nothing migrates now.

Specifically, do **not** migrate:

- Alpha158 as an official family;
- LightGBM parameters;
- TopkDropoutStrategy parameters;
- CSI300 performance;
- Qlib cost defaults;
- community-data claims.

Retain Qlib externally as:

`NONLINEAR_FACTOR_DISCOVERY / SUPERVISED_ML_SANDBOX / FACTOR_DIAGNOSTICS_COMPONENT`

If a QRDS-governed cross-sectional panel becomes available later, Qlib is a strong candidate for a bounded, preregistered confrontation.

## Scientific boundary

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL=0`
- no engine feed
- no automatic promotion
- no external performance import
- no retune from standalone outcome

## Final status

`Qlib = CONCLUDED / RETAIN_AS_NONLINEAR_FACTOR_RESEARCH_SANDBOX`

Standalone: **PASS**.

Integrated confrontation: **scientifically blocked by dataset geometry / history, not forced**.
