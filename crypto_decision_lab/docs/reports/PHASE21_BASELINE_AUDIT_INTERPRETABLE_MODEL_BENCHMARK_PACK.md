# QRDS/QOS Phase 21 Baseline Audit + Interpretable Offline Model Benchmark Pack

Sprint 21A–21Z combines:

1. Phase 20 baseline/null-model audit;
2. Offline interpretable model benchmark.

Inputs:

- Phase 20 baseline/null metrics;
- Phase 19 offline experiment harness.

Model families:

- simple linear return model;
- momentum/volatility/dispersion return model;
- volatility/dispersion absolute-return model;
- current volatility proxy model;
- multi-feature realized-volatility model.

Outputs:

- per-coin model metrics;
- per-coin coefficient files;
- combined model metrics;
- combined coefficients;
- baseline-comparison fields.

Safety constraints:

- offline research training only;
- no operational prediction rows;
- no trading signal;
- no recommendation;
- no allocation;
- no operational decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.
