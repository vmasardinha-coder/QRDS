# QRDS/QOS Phase 20 Baseline Metrics + Null Models Harness Pack

Sprint 20A–20R establishes research-only null/baseline metrics before any real model training.

Inputs:

- Phase 19 offline experiment harness CSVs.

Outputs:

- per-coin baseline/null metrics;
- combined baseline metrics CSV;
- zero-return control;
- train mean/median baselines;
- regime-mean baselines;
- current volatility proxy baseline;
- shuffled train-distribution controls;
- train/validation/holdout metrics;
- leakage guards;
- project status update.

Safety constraints:

- no model training;
- no model predictions;
- baselines are not trading signals;
- targets are not signals;
- no recommendation;
- no allocation;
- no operational decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.
