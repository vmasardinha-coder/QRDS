# Factory Delta C1

Issue #165 implementation. This line never mutates the current Delta incumbents. It preregisters five isolated mechanism families and runs them on causal public OHLC inputs with a fixed historical cutoff, discovery/replication split, next-bar semantics, fixed costs, robustness neighbor requirement and independent replication requirement.

Outputs are research-only. Version 2 uses weights selected at the preceding completed close to measure each daily return. Rebalance costs are charged at the new decision close; the new exposure begins next bar. Missing closes are never forward-filled, and an unobservable held return blocks the affected discovery or replication gate.

Version 1 incorrectly credited the signal-forming bar to the new weights. The four previously reported candidates were confirmed as **synthetic fixture** output in run 32774705275 / job 97582982497 on 2026-08-24. They were not canonical public-data survivors. The preexisting C2 preregistration already assigned C1 zero predecessor credit because its result evidence was not canonically persisted.

`gate_btc_factory/DELTA_C1_CLOSURE_20261022.v1.json` closes the old generation as `CLOSED_NO_CANONICAL_SURVIVOR_EVIDENCE`, with zero candidates awaiting freeze, zero admission and zero scientific rejection/promotion credit. Do not download fresh historical data to rescue C1. A genuinely new generation requires separate pre-results source qualification and preregistration. Preserve the historical preregistration and records; do not relabel them as version 2 or as economic rejections.

The recurring public schedule is removed. Manual fixture QA remains available. A legacy `--mode public` invocation writes only the sealed terminal receipt and performs no network collection or evaluation.

Passing version 2 metrics produces `CAUSAL_CANDIDATES_REQUIRE_SOURCE_QUALIFICATION`, with `freeze_eligible=false` and `legacy_v1_admission_allowed=false`. Fixture data cannot authorize a freeze. Freeze/prospective binding remains a separate transition with D0 strictly after freeze and no backfill. Comparative capital is normalized to R$180,000 only in the reporting/comparison layer.
