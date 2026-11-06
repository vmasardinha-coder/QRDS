# Momentum M1/M2 duplicate-cutoff hash root cause

Status: OPERATIONAL_REPAIR_ONLY / SCIENCE_FROZEN
Cutoff under reproduction: 2026-08-26
Existing append-only anchor: `6a3c61297695eb47383dd46298df714766a16f37848df256c805503040dbeec5`

## Root cause

Two independent non-deterministic dependencies existed in the collector identity path.

1. `snapshot_sha256` hashed `source.member_sha256` and `source.v2a_zip_sha256`. Those hashes cover the full current CSV/ZIP bytes, including rows and container bytes after a historical cutoff. Rebuilding the same cutoff later can therefore change snapshot identity even when every cutoff-admissible scientific input and M1/M2 output is unchanged.

2. The collector selected the lexicographically latest ledger JSON as the predecessor. On the first append of 2026-08-26 the predecessor was 2026-08-25, so the persisted snapshot contains M1 and M2 `delta_breadth_pct_points` versus 2026-08-25. On a duplicate reconstruction the latest file can be 2026-08-26 itself (or a later cutoff), so the historical predecessor calculation is different. The target snapshot was therefore changing the reconstruction of itself.

These are operational identity/replay defects. No Momentum formula, universe rule, signal, threshold, cost, gate, cutoff, or scientific parameter is changed.

## Repair

- Scientific identity is canonical JSON with stable key ordering, UTF-8, LF and non-finite-number rejection.
- M1/M2 cross-sectional row order is canonicalized by asset; scientific rank fields remain identity-bearing.
- Full current archive/member hashes remain persisted as audit provenance, but are excluded from historical scientific identity because they are not cutoff-causal.
- Source member identifier and cutoff-filtered row count remain identity-bearing.
- Full M1/M2 rows, summaries, explicit ranks and safety fields remain identity-bearing.
- Historical predecessor is always the greatest ledger cutoff strictly less than the requested cutoff. The target cutoff and later snapshots are excluded from that calculation.
- A duplicate with scientifically identical canonical content is an append-only no-op and retains the original persisted anchor hash; ledger bytes are not rewritten.
- Any scientific canonical difference remains a hard fail and emits a structural conflict diagnostic outside the ledger.
- A new retroactive cutoff remains forbidden.

## Immutable boundaries

`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `ENGINE_FEED=false`.

No H1 economics or partial prospective survivor economics are read. H31 and all frozen survivors/results are out of scope.
