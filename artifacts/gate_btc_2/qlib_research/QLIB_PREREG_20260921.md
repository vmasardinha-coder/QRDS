# Qlib standalone preregistration — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true  
REAL_CAPITAL=0

## System

- upstream: `microsoft/qlib`
- release: `v0.9.7`
- upstream SHA: `da920b7f954f48ab1bb64117c976710de198373e`
- role under test: nonlinear factor / supervised-ML research platform

## Tangible question

Can Qlib, without any QRDS integration or post-outcome tuning, produce a complete reproducible research artifact consisting of:

1. Alpha158 features;
2. LightGBM forecasts;
3. IC / Rank-IC signal diagnostics;
4. a costed portfolio backtest;
5. drawdown / information-ratio style risk metrics;
6. an immutable run log and data archive SHA.

This is a **standalone capability test**, not a Factory alpha admission.

## Frozen upstream benchmark

Use the exact upstream `examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml` from the pinned SHA without parameter changes.

Frozen benchmark semantics from upstream config:

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

No hyperparameter search. No alternate model after seeing output. No date changes. No cost changes.

## Data boundary

Qlib's official prebuilt dataset is currently unavailable upstream, so the run uses the community-maintained Qlib-format China-stock archive linked by the Qlib project documentation. The downloaded archive is hashed (`sha256`) before extraction and that hash is preserved in the artifact.

This means any positive result proves **Qlib workflow capability**, not authoritative market-data provenance suitable for Factory admission.

## Pass / fail interpretation

`CAPABILITY_PASS` requires the frozen workflow to complete and emit signal-analysis and portfolio-analysis output. A positive return is **not** required for a capability pass.

Any economic claim remains external/reference-only until the same class of model is retested on independently governed QRDS data with Factory PIT/leakage/cost/holdout rules.

## Prohibited conclusions

This run cannot establish that:

- Qlib is superior to QRDS;
- Alpha158 is a Factory survivor;
- LightGBM is a Factory survivor;
- the CSI300 result generalizes to BTC/B3;
- upstream or community data is sufficiently PIT-safe for Factory use.

The only admissible next step after a clean standalone result is a separately frozen integrated/confrontation test on QRDS-governed data.
