# QRDS/QOS Phase 19 Offline Experiment Harness Pack

Sprint 19A–19R prepares research-only offline experiment datasets from Phase 18 features.

Inputs:

- Phase 18 research feature/regime diagnostics CSVs.

Outputs:

- chronological train/validation/holdout splits;
- forward 24h research target columns;
- feature/diagnostic column manifest;
- leakage guards;
- harness dashboard and status update.

Safety constraints:

- no model training;
- no predictions;
- research targets are not signals;
- no trading signal;
- no recommendation;
- no allocation;
- no operational decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.
