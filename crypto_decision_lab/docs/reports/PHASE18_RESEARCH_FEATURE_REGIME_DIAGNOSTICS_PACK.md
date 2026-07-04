# QRDS/QOS Phase 18 Research Feature + Regime Diagnostics Pack

Sprint 18A–18R builds a research-only feature layer on top of validated consensus data.

Inputs:

- Phase 17 consensus quality/drift monitor;
- Phase 16 consensus CSVs.

Outputs:

- per-coin research feature CSVs;
- returns and log returns;
- rolling annualized volatility;
- rolling momentum diagnostics;
- drawdown from peak;
- source dispersion features;
- research-only regime labels.

Safety constraints:

- diagnostic labels are not signals;
- no trading signal;
- no recommendation;
- no allocation;
- no operational decision;
- no safe-apply;
- no canonical promotion;
- zero canonical writes.
