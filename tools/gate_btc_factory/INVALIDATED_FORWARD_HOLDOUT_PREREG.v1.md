# Invalidated-family forward holdout requalification

Status: **PREREGISTERED BEFORE REQUALIFICATION ECONOMICS**

This repair does not reinterpret or overwrite the invalidated H1962-H2729 historical results. Those results remain append-only evidence of a mechanically defective scientific run.

The existing frozen family contracts are re-evaluated in a new namespace only because the original evaluator was mechanically restricted to discovery 2022-2024 and replication 2020-2021. The candidate repair dataset is the published WINFUT M5 series from `wesleyzilva/tradetech`, pinned to immutable commit `e891c7be2257b4ff439d04661df1971e6df19684`, and only timestamps strictly before the canonical exclusive cutoff `2026-08-10` are eligible.

The holdout builder must fail closed unless all 768 affected family IDs are found in the historical result archive and none of their original discovery/replication payloads contains 2025 or 2026 evaluation evidence. It must also fail closed unless the candidate series provides at least 322 structurally valid M5 sessions, allowing two disjoint windows of at least 161 sessions each. The split is determined only by ordered eligible session dates, never by economics.

The first chronological window is discovery and the second chronological window is temporal replication. The same normalized, hash-bound dataset may serve all family batches, but each scoped source gate declares only its assigned family IDs. Batch partition is mechanical: ascending canonical affected-family order, 64 families per batch, 12 batches total. Batch boundaries have no economic meaning.

This is a new evaluation namespace, not a same-window rerun and not historical backfill credit. No old observation counts are imported. Threshold, feature, direction, decision window, holding horizons, causal standardization, costs, cutoff and PIT rules remain exactly those frozen in each original family contract. No partial economics may influence source qualification, batching, windows or contracts.

Safety remains immutable: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `NO_COUNTER_RESET=true`, `FAIL_CLOSED=true`, `H1_ECONOMICS_READ=false`.

A family can terminate only through the existing requalification pipeline as scientific rejection or a valid survivor ready for a separate forward-only prospective shadow ledger. Source/plumbing repair alone cannot promote a survivor.
