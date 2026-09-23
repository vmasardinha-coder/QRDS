# XAGENT signal binding audit — 2026-09-22

## Result

`F-XAGENT-DISAGREE` cannot yet be bound to three existing QRDS signals without introducing new scientific semantics.

The audit used provenance, independence, causal availability and pre-existing signal semantics only. No PnL, effect, Sharpe, hit rate or historical winner ranking was used to select a binding.

## Why existing channels do not yet form an admissible trio

- `H626/H478/H474`: monitoring families emit feature/z/trigger semantics, not a pre-existing directional producer frozen in `[-1,+1]`; additionally H478 and H474 share `OPEN_RANGE`, so they are not independent evidence channels.
- `F-XMM-INVENTORY`: live microstructure extractor and explicit abstention semantics exist, but `economic_direction`, thresholds and aggregation window remain intentionally undefined. Turning its features into a directional `[-1,+1]` signal would be a new hypothesis.
- `F-XVOL-SURFACE`: live options-surface extractor and explicit abstention semantics exist, but `economic_direction`, thresholds and lookbacks remain intentionally undefined. Turning the surface into a directional `[-1,+1]` signal would be a new hypothesis.
- `H-XREGIME-01 Batch A`: historically closed with zero discovery passes and no retune; its gate states were not preregistered as reusable normalized directional producers.

Therefore there is currently no outcome-blind existing trio that satisfies the XAGENT intake contract.

## Next scientific lane

Use the already-frozen Factory Parallel Frontier contract rather than manually inventing three signals. The PF dispatcher must remain outcome-blind and select the first novel grammar signature in ascending order, under `PF::`, with zero historical/retroactive credit and no promotion authority.

Next gate:

`GRAMMAR_SCOUT_OUTCOME_BLIND_HANDOFF -> SOURCE_QUALIFICATION -> SEPARATE_CHILD_PREREGISTRATION`

Only after independent upstream signal producers are preregistered and source-qualified may they become candidates for `F-XAGENT-DISAGREE` binding.

## Safety

`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `H1_H31_UNTOUCHED=true`.
