# GATE BTC B3 Autonomous Science Protocol v1

Status: FROZEN_BEFORE_H170_ECONOMICS

Purpose: allow the Factory to create new B3 research families without human intervention while preserving preregistration, causal separation and fail-closed governance.

## Frozen loop

1. Read the latest canonical closed decade frontier Hxx0-Hxx9.
2. Materialize the next decade from this protocol only. No economic result may influence family construction.
3. Build exactly ten family contracts, one per H number in the decade.
4. Execute discovery and independent replication on pre-H1 data only.
5. Publish at most two replicated survivors; null is valid.
6. Write a canonical terminal result.
7. Advance to the next decade automatically.

## Frozen family grammar

All signals use WIN M5 intraday translation-invariant data admitted by the existing Stage1 adapter. Decision features are computed only from bars available at the decision timestamp. Each raw feature is standardized causally with a rolling 20-session median and MAD using prior sessions only. No forward fill, interpolation, synthetic backfill or H1 economics read is allowed.

Feature universe, fixed order:
`OPEN_RETURN`, `OPEN_RANGE`, `REALIZED_VOL`, `VOLUME_EARLY`, `BAR_IMBALANCE`, `CLOSE_LOCATION`, `BODY_RANGE`, `GAP_FROM_PRIOR_CLOSE`.

Directions, fixed order: `CONTINUATION`, `REVERSION`.

Decision windows, fixed order: 15, 30, 60, 90 minutes.

Absolute z thresholds, fixed order: 0.75, 1.00, 1.25, 1.50.

The Cartesian product is ordered lexicographically in exactly that field order. Family H170 consumes universe element 0, H171 element 1, and so on. Therefore family construction is deterministic and independent of all future economics. The protocol must fail closed on universe exhaustion; extending the grammar requires a new version frozen before reading results beyond the exhausted frontier.

Fixed holding horizons: 30, 60, 120 minutes.

Fixed economics gates per cell: >=60 trades; reference cost 2 bp; net mean >0.25 bp; stress cost 3 bp net >0; one-bar delayed entry net >0; both long and short >=15 trades and positive at 2 bp; at least two calendar half-year buckets with >=15 trades and positive at 2 bp; top-5 positive-gross concentration <=40%.

Family discovery survivor: >=2 qualified holding-horizon cells. Independent replication must satisfy the same family rule. Max two survivors per generation, selected by ascending family id only, never by performance rank.

Fixed data split: independent replication = sessions in 2020-2021; discovery = sessions in 2022-2024. Both are strictly pre-H1 cutoff 2026-08-10.

## Safety

`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `ENGINE_FEED=false`, `H1_ECONOMICS_READ=false`.

Operational recovery may retry source/plumbing failures. It may never alter this grammar, thresholds, split, cost model, family ordering or cutoff.
