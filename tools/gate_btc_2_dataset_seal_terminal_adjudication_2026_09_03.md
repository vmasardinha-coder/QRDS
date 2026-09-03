# GATE BTC 2.0 — terminal adjudication of the original historical Dataset Seal

Date: 2026-09-03
Issue: #111
Scope: read-only scientific adjudication under the already-frozen Dataset Seal contract. No new dataset epoch is created by this checkpoint.

## Frozen safety/methodology boundary

- RESEARCH_ONLY=true
- SHADOW_ONLY=true
- NOT_APPROVED=true
- ENGINE_FEED=false
- ORDERS=0
- REAL_CAPITAL_BRL=0
- NO_RETUNE=true
- NO_BACKFILL=true
- NO_COUNTER_RESET=true
- NO_SILENT_SOURCE_SUBSTITUTION=true
- FAIL_CLOSED=true

## Existing canonical evidence

1. The 16-system Master Plan records terminal PIT reconstruction of `9819/10254` expected observations (~95.76%) and explicitly preserves unresolved PIT/survivorship gaps as evidence.
2. Satisfiability audit #416 classifies unresolved historical PIT observations as `IMPOSSIBLE_TO_RETROACTIVELY_REPAIR_WITH_NO_BACKFILL` and historical survivorship bias as `NOT_RESOLVED_BY_PROSPECTIVE_SOURCE_QUALIFICATION`.
3. Semantic audit #417 found `0/22` current semantic-scope cases eligible for deterministic exclusion under pre-existing frozen universe rules, so post-hoc denominator pruning is forbidden.
4. The current Dataset Seal readiness implementation independently requires all of the following for the V2A scope:
   - point-in-time coverage `>= 1.0`; otherwise blocker `V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE`;
   - `loaded == attempted`; otherwise blocker `V2A_SYMBOL_LOAD_GAP`;
   - `survivorship_bias_present == false`; otherwise blocker `V2A_SURVIVORSHIP_BIAS_PRESENT`;
   - future-PIT and no-retrospective-backfill policies remain frozen.
5. Latest authoritative runtime evidence remains below complete PIT coverage and preserves `survivorship_bias_present=true`. New source qualifications have explicitly been adjudicated as forward/prospective collection-path evidence only and do not rewrite historical PIT snapshots.

## Satisfiability proof

Let the original historical seal pass require the conjunction of its frozen V2A readiness predicates. At least two required predicates are already independently unsatisfied by immutable historical evidence:

- complete point-in-time coverage is false because unresolved contemporaneous PIT observations remain absent;
- absence of survivorship bias is false in the frozen historical snapshots.

Under `NO_BACKFILL=true`, a source discovered or downloaded after the historical observation time cannot convert an absent contemporaneous PIT observation into an observation that existed at that past decision time. Likewise, qualifying a present-day exchange/source cannot remove survivorship bias from already-frozen historical universe snapshots.

Therefore, even if every remaining `SOURCE_RECOVERY_CANDIDATE` acquired a clean public source today and the current symbol-load gap became zero, the original historical Dataset Seal would still fail at least `V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE` and `V2A_SURVIVORSHIP_BIAS_PRESENT` under its existing contract.

Remaining source qualification is still useful for forward collection health and future dataset design. It is no longer a logically necessary prerequisite for deciding whether the **original historical seal** can pass.

## Terminal scientific outcome

`ORIGINAL_HISTORICAL_DATASET_SEAL = UNSEALED_FAILED`

Reason: `FROZEN_READINESS_CONTRACT_UNSATISFIABLE_UNDER_NO_BACKFILL`

This is a scientific FAIL, not an operational error and not permission to relax the gate. The negative historical evidence is preserved permanently. No challenger economics are unlocked by this outcome.

## Roadmap consequence

- System 8 original historical Dataset Seal checkpoint is scientifically closed as `FAIL / UNSEALED` rather than left in an endless recovery loop.
- Existing and newly qualified public sources may continue as forward collection-path improvements, independently and without historical credit.
- System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE` under its already-frozen admitted forward clock; its required N is not changed.
- Systems 10–14 remain dependency-bound until the admissible forward data/microstructure foundations satisfy their own gates.
- System 15 remains independent and parallel.
- System 16 remains `FUTURE_CONTROLLED`.

## Human-decision boundary

Audit #416 explicitly did **not** authorize creation of a replacement dataset epoch. With the original historical seal now terminally adjudicated `UNSEALED_FAILED`, the only scientifically clean route to an eventually sealable System 8 dataset is a separate **prospectively preregistered dataset epoch** with a future cutover, frozen universe/source contracts, causal PIT collection from inception, independent readiness clock, and zero credit from the failed historical seal.

Creating/activating that new epoch changes the dataset methodology/clock and therefore requires explicit human authorization. This checkpoint does not create it.
