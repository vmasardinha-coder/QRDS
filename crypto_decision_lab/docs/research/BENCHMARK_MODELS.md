# Benchmark Model Comparison

Sprint 7F adds deterministic benchmark model comparison.

It compares simple research-only predictors:

```text
zero_prediction
train_mean
train_median
last_train_value
```

## Purpose

A future model must beat simple baselines before it is worth deeper research.

## Not allowed

These benchmarks are not:

```text
trading signals
orders
recommendations
position sizing
live strategy
operational decisions
```

## Metrics

Regression targets:

```text
MAE
RMSE
```

Binary targets:

```text
accuracy
MAE
RMSE
```

The ranking is research-only and non-operational.
