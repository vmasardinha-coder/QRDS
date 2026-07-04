# QRDS/QOS Phase 17 Consensus Quality + Drift Monitor Pack

Sprint 17A–17R checks the quality of the Phase 16 multi-source consensus baseline.

Inputs:

- Phase 16 consensus CSVs;
- ready sources embedded inside consensus rows;
- source deviation columns.

Outputs:

- per-coin dispersion summaries;
- source deviation summaries;
- outlier rate by source;
- rolling 24h and 168h dispersion;
- consensus volatility and drawdown research metrics;
- dashboard report.

Safety constraints:

- no trading signal;
- no recommendation;
- no allocation;
- no operational decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.
