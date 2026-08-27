# Momentum M1/M2 — 2026-08-26 duplicate-cutoff hash conflict

Status: **FAIL_CLOSED / HISTORICAL_INPUT_MISMATCH**

## Scope

Operational investigation only. No scientific rule, cutoff, universe rule, signal, threshold, cost, gate, H1 economics, survivor economics, order path, capital path, engine feed, H31 state, historical scientific result, or append-only ledger entry was changed.

## Reproduction

Validation workflow run `33123706296` used one public V2A collection, froze it to cutoff `2026-08-26`, copied the exact frozen ZIP bytes into RUN A and RUN B, and ran the deterministic candidate collector against two independent copies of the runtime ledger.

Both RUN A and RUN B failed closed with the same candidate scientific identity:

`d59088e350b0b7502bfb6eeacf25c677716d2906eba1810860df6dae97924159`

Persisted legacy snapshot hash for cutoff 2026-08-26:

`6a3c61297695eb47383dd46298df714766a16f37848df256c805503040dbeec5`

The original ledger bytes remained unchanged in both copies.

## Exact root cause

There were two independent sources of operational non-determinism in the legacy duplicate-cutoff path:

1. Snapshot identity included volatile provenance hashes for the full V2A ZIP/member container. These bytes can change when the public package is rebuilt later even if the scientifically relevant cutoff content is unchanged.
2. The legacy predecessor lookup could select the target cutoff itself during a duplicate reconstruction, so `delta_breadth_pct_points` was not reconstructed against the strict prior cutoff.

Those two defects are mechanically correctable and are covered by deterministic canonicalization tests on the repair branch.

However, after removing those operational effects, the current public source still does **not** reproduce the scientific content of the persisted 2026-08-26 snapshot.

### Historical input mismatch evidence

Persisted snapshot source member SHA256:

`d8a6794472b95e1b66145c9e6621aa5f5f6ef25c33735e8e4d48eddf31688a36`

Current frozen replay source member SHA256 for the same cutoff:

`78444eabd75cfaec5aff8d8a9dfafa4951af99f4aa11b675fc10594359f6a282`

Persisted M1 universe size: **93**.
Current reconstructed M1 universe size: **92**.

`RUNE` is present in the persisted 2026-08-26 snapshot but absent from the currently reconstructable source at that cutoff. Removing that member changes cross-sectional z-scores and ranks for the remaining universe.

The mismatch is not limited to universe membership. `2Z` historical prices/returns have also changed in the current source reconstruction:

- persisted `2Z.r14 = 0.20396959459459474`
- current `2Z.r14 = 0.22804054054054057`
- persisted `2Z.r30 = -0.03584714237402764`
- current `2Z.r30 = -0.016570848833276863`

For controls, assets such as AAVE and STX reproduce their raw 14/30-day returns, while their cross-sectional z-scores/ranks can still change because the effective universe no longer contains RUNE.

Therefore the current source is a different historical input, not merely a differently ordered/serialized representation of the same admissible data.

## Integrity decision

No canonicalization may legally synthesize RUNE, overwrite revised 2Z history, substitute another universe, or force the candidate hash to the persisted hash. The 2026-08-26 duplicate remains a hard fail.

Classification: `PERSISTENT_OPERATIONAL_BLOCKER / duplicate-cutoff-hash-conflict`
Root-cause terminal classification: `HISTORICAL_INPUT_MISMATCH`

The correct final state is fail-closed until an independently verifiable copy of the exact historically admissible 2026-08-26 source input can reproduce the persisted snapshot.

## Regression evidence

The repair branch tests cover:

- same cutoff + same data -> same hash;
- non-semantic row order changes -> same hash;
- volatile operational metadata -> no identity change;
- real scientific data change -> different hash;
- duplicate same scientific identity -> idempotent no-op;
- duplicate different identity -> hard fail;
- incomplete/non-finite input -> fail closed;
- safety boundary with no protected economics reads;
- strict predecessor lookup excludes target and future snapshots;
- retroactive *new* cutoff remains forbidden.

Validation run `33123706296`: all 13 deterministic/unit regressions passed before the real historical reproduction. The real historical reproduction then correctly failed closed in both A and B with the same candidate identity.

## Safety invariants

- ledger mutated: false
- scientific rules changed: false
- H1 economics read: false
- prospective survivor economics read: false
- orders: 0
- capital: 0
- engine feed: false
