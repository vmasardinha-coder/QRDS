# Factory Delta C1

Issue #165 implementation. This line never mutates the current Delta incumbents. It preregisters five isolated mechanism families and runs them on causal public OHLC inputs with a fixed historical cutoff, discovery/replication split, next-bar semantics, fixed costs, robustness neighbor requirement and independent replication requirement.

Outputs are research-only. Version 2 uses weights selected at the preceding completed close to measure each daily return. Rebalance costs are charged at the new decision close; the new exposure begins next bar. Missing closes are never forward-filled, and an unobservable held return blocks the affected discovery or replication gate.

Version 1 incorrectly credited the signal-forming bar to the new weights. Its four previously reported candidates remain historical records, but are not eligible for freeze or admission. They require a version 2 replay using the original frozen source bytes and separate source qualification. The historical preregistration and old results must not be overwritten or relabeled as version 2.

Passing version 2 metrics produces `CAUSAL_CANDIDATES_REQUIRE_SOURCE_QUALIFICATION`, with `freeze_eligible=false` and `legacy_v1_admission_allowed=false`. Fixture data cannot authorize a freeze. Freeze/prospective binding remains a separate transition with D0 strictly after freeze and no backfill. Comparative capital is normalized to R$180,000 only in the reporting/comparison layer.
