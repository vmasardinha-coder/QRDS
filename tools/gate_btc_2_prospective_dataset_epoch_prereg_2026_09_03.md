# GATE BTC 2.0 — prospectively preregistered replacement Dataset Epoch

Date authorized: 2026-09-03
Issue: #455
Historical authority: #111 / merged terminal adjudication #453
Status at preregistration: `AUTHORIZED_PREREGISTERED_WAITING_CUTOVER_GATE`

## Purpose

Open a scientifically separate replacement Dataset Epoch after the original historical Dataset Seal was terminally adjudicated `UNSEALED_FAILED / FROZEN_READINESS_CONTRACT_UNSATISFIABLE_UNDER_NO_BACKFILL`.

This epoch is forward-only. It does not repair, rewrite, reset, reinterpret, or inherit scientific/prospective credit from the failed historical seal.

## Frozen safety boundary

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

No challenger economics, survivor promotion, live engine feed, orders, or real capital are authorized by this epoch opening.

## Frozen methodological boundary

1. **Family/scope:** retain the existing GATE BTC 2.0 `MULTIASSET_V2A` dataset family and its pre-existing frozen universe/identity contract. No post-hoc universe additions, removals, denominator pruning, direction changes, threshold changes, cost changes, hold changes, cutoff changes, or PIT-semantic changes are authorized.
2. **Universe freeze:** the epoch universe is the exact canonical V2A universe/identity contract that exists at the activation/cutover commit. Any ambiguity remains fail-closed; no outcome-aware exclusion is allowed.
3. **Source contracts:** only exact-identity, auditable, causally available sources admitted under the existing source-qualification rules may support the cutover gate. Source identities and priority/fallback contracts are frozen at D0. No silent substitution is permitted.
4. **PIT causality:** an epoch observation earns credit only when captured by the canonical forward collector at or after its real observation time under the frozen availability/cutoff semantics. Nothing downloaded later may be inserted into an earlier epoch timestamp.
5. **No historical inheritance:** historical #111 observations, reconstructed panels, historical source qualifications, and the failed seal contribute zero observations and zero readiness/prospective/scientific credit to this epoch. They may remain read-only diagnostics only.
6. **Independent readiness clock:** this epoch has its own readiness clock. It is not a reset of any previous counter and does not alter any other system clock.

## Cutover / D0 gate

Preregistration is effective immediately after merge, but scientific D0 is deliberately **not** assigned a retroactive date.

`D0 = first successful canonical post-preregistration observation for which the entire frozen V2A universe is captured as one causally admissible PIT snapshot using qualified exact source contracts and all frozen readiness-integrity predicates required at cutover pass.`

Until that event occurs:

- epoch state remains `AUTHORIZED_PREREGISTERED_WAITING_CUTOVER_GATE`;
- existing authorized forward collectors/source qualification may continue unchanged;
- pre-D0 captures are plumbing/health/rehearsal evidence only;
- no pre-D0 row may later be promoted into epoch credit;
- no new duplicate collector/workflow is to be created merely to manufacture D0.

If a complete causal cutover snapshot cannot be produced, the epoch stays waiting/fail-closed rather than weakening the universe or backfilling gaps.

## D0 freeze record

At the first passing cutover event, the canonical runtime must emit an immutable D0 record containing at minimum:

- epoch identifier;
- activation/preregistration commit SHA;
- D0 observation timestamp and timezone;
- frozen universe/identity contract reference and digest;
- exact source contract registry reference and digest;
- per-symbol source identity used at D0;
- raw/immutable capture references and hashes;
- schema/timezone/cutoff/PIT checks;
- duplicate/missing-row and monotonicity QA;
- explicit observed-vs-derived labeling;
- confirmation `backfill_performed=false`;
- confirmation `historical_credit=0`, `prospective_credit_before_D0=0`;
- safety flags and `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL_BRL=0`.

The D0 record is append-only/frozen once emitted. It may not be rewritten to improve later readiness.

## Post-D0 scientific pipeline

After D0, only new forward observations from the frozen epoch contract may advance dataset readiness. The pipeline remains:

`DATA -> PREREGISTER -> DISCOVERY -> BIAS/CAUSALITY QA -> ROBUSTNESS -> INDEPENDENT REPLICATION -> REJECT/FREEZE -> SEPARATE PROSPECTIVE -> REPORT`

For System 8 specifically, dataset readiness/seal must be independently satisfied before any downstream challenger economics can be opened. Null/failure remains valid and does not justify retuning.

## Non-interference / orchestration

- Reuse native forward collection and source-qualification plumbing where already present.
- Do not duplicate workflows that already deliver the required observations.
- Repairs are limited to authorized plumbing/orchestration/data-delivery and may not earn scientific credit.
- A repair cannot promote a source, survivor, dataset seal, or clock state by itself.
- Existing System 9 and all other scientific clocks remain unchanged.

## Historical seal permanence

`ORIGINAL_HISTORICAL_DATASET_SEAL = UNSEALED_FAILED`

Reason: `FROZEN_READINESS_CONTRACT_UNSATISFIABLE_UNDER_NO_BACKFILL`

This value is permanent and is not superseded by eventual success or failure of this replacement epoch.
