# Diagnostic suspicion after H2-H29

Repeated nulls do not by themselves imply an infrastructure defect. H14-H29 demonstrated nonzero signal generation and isolated qualified cells on WIN, which argues against a trivially dead evaluator; WDO was much weaker. However, before interpreting another null as market evidence, H30-H39 explicitly records and tests three plausible research bottlenecks:

1. Single-asset information insufficiency: prior families mostly used one instrument's OHLCV state. H30-H39 tests relative/cross-asset information.
2. Continuous-series / coarse-bar limitations: scale-invariant rules and independent 5m-vs-15m replication reduce but do not eliminate microstructure/roll distortion. No absolute cross-asset price-level feature is allowed.
3. Gate severity versus true weak edge: gates remain frozen intentionally. We will inspect rejection-reason distributions and qualified isolated cells, but will not relax thresholds after seeing outcomes.

A fourth concern is synchronized coverage. The runner reports common-bar coverage and returns DATA_INADEQUATE if discovery <300 synchronized sessions, replication <600, or median common-bar coverage <95%.

This note is diagnostic only and does not authorize changing H1, costs, gates, cutoff, or promotion criteria.
