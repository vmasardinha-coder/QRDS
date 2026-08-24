# Factory Delta C1

Issue #165 implementation. This line never mutates the current Delta incumbents. It preregisters five isolated mechanism families and runs them on causal public OHLC inputs with a fixed historical cutoff, discovery/replication split, next-bar semantics, fixed costs, robustness neighbor requirement and independent replication requirement.

Outputs are research-only. A replicated survivor is only `SURVIVORS_READY_FOR_FREEZE`; freeze/prospective binding is a separate automatic factory transition with D0 strictly after freeze and no backfill. Comparative capital is normalized to R$180,000 only in the reporting/comparison layer.
