# Invalidated-family forward holdout requalification

Status: **PREREGISTERED BEFORE VALID REQUALIFICATION ECONOMICS**

The invalidated H1962-H2729 historical results remain append-only evidence of a mechanically defective run and are never rewritten.

The original evaluator was restricted to discovery 2022-2024 and replication 2020-2021. Therefore the repair namespace is restricted to **2025-01-01 through 2026-08-09 only**. No 2024 observation is eligible. This strict boundary corrects and supersedes the first attempted gate build, whose 2024 overlap was interlocked before runtime result publication and receives zero scientific or survivor credit.

The source is the public Neologica Profit WINFUT M5 export in `wesleyzilva/tradetech`, assembled only from immutable pinned Git objects: `CandlesHistoryDatas/2024_26/WINFUT_F_0_5min.csv` at `e891c7be2257b4ff439d04661df1971e6df19684` plus `CandlesHistoryDatas/CandlesHistoricos2026/WINFUT_F_0_5min.csv` at `0deb43c668dcd447ed169c9cafb52af625d5419e`. Duplicate timestamps must be byte-equivalent after normalization or the build fails closed.

The builder must fail closed unless all 768 affected family IDs are present in the historical archive, none of their original discovery/replication payloads contains 2025 or 2026 evaluation evidence, and the strict 2025+ series supplies at least 322 structurally valid M5 sessions. This permits two chronological, non-overlapping windows of at least 161 sessions each. The split is determined solely by ordered eligible session dates, never by economics.

The first chronological window is discovery and the second is temporal replication. The normalized dataset is hash-bound. Family routing is mechanical: canonical affected-family order, 64 families per scoped gate, 12 gates total. Batch boundaries have no economic meaning.

This is a new evaluation namespace, not a same-window rerun and not historical backfill credit. Threshold, feature, direction, decision window, holding horizons, causal standardization, costs, cutoff and PIT remain exactly those frozen in each original family contract. No partial economics may influence source qualification, batching, windows or contracts.

Safety remains immutable: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `NO_COUNTER_RESET=true`, `FAIL_CLOSED=true`, `H1_ECONOMICS_READ=false`.

A family can terminate only through the existing requalification pipeline as scientific rejection or a valid survivor ready for a separate forward-only prospective shadow ledger. Source/plumbing repair alone cannot promote a survivor.
