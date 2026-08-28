# GATE BTC 2.0 — Evidence Factory MVP (EF-A0..EF-A5)

## Placement

The Evidence Factory is an additive scientific-orchestration layer activated after the shared Collector Supervisor foundation. It does **not** replace or interrupt the Strategy Factory and is not a new strategy-generation stage.

`Strategy Factory -> frozen candidate -> Evidence Factory -> scientific evidence decision`

The Strategy Factory remains free to continue discovery. The Evidence Factory receives only an already-frozen candidate.

## Mission boundary

Evidence Factory mission: **PROVE OR REFUTE EVIDENCE**.

It may bind a frozen candidate and hashes, derive a deterministic evidence checklist, detect missing/failed evidence, reference existing scientific authorities, maintain a fail-closed state machine, emit prospective requirements, consume shared Collector Supervisor health/counters, project readiness into Executive Items 1B/6/10/11/12/13, and stop at `HUMAN_PROMOTION_REVIEW` after a full research pass.

It may not generate Hxxx strategies, retune a failed hypothesis, change methodology after results, synthesize/backfill prospective evidence, silently substitute a source, duplicate PIT/source-admission/survivorship/stress logic, own all collectors, duplicate economics/Monte Carlo, feed the engine, create orders, use real capital, or automatically promote.

## MVP checkpoints

### EF-A0 — Frozen handoff
A candidate binds candidate/version, hypothesis hash, config hash, code hash, cutoff, D0, source identity and originating Strategy Factory artifact hash. Missing identity/hash information fails closed. The checklist is deterministic.

### EF-A1 — Evidence gap engine
Each required evidence type resolves to `PASS`, `FAIL`, or `COLLECT_MORE` plus a deterministic next state. Negative evidence closes the frozen hypothesis and cannot invoke retuning.

### EF-A2 — Existing authority adapters
The MVP references rather than copies canonical authorities already present:
- Selector Alpha terminal proof for PIT/survivorship/stress patterns;
- Gate BTC 2 source-admission adapter for provenance/admission;
- Factory Collector Supervisor (#221 / PR #232) for operational health.

Authority files are hash-inventoried. A missing authority is an evidence-infrastructure gap, never permission to substitute logic.

### EF-A3 — State machine
Transitions cover frozen hypothesis, historical/PIT, data/source gaps, robustness, replication, prospective evidence, economics readiness and human review. Transitions are hash-linked. Terminal scientific states cannot transition back into research to rescue a failed hypothesis.

### EF-A4 — Prospective requirements + shared Supervisor
The Evidence Factory does not own collectors. `COLLECT_MORE` emits `required_data`, `source`, `frequency`, `required_N`, `current_N`, `target_gate`, and `earliest_decision_date`, consuming canonical `qrds.factory.collector_health.v1` health/counters.

**Stage 9 rule:** contract/builder/workflow existence is not prospective evidence. Until an authorized forward-only capture is actually observed and admitted, Stage 9-dependent evidence remains `COLLECT_MORE`/blocked. Historical recovery gets zero prospective credit.

### EF-A5 — Executive projection + human handoff
Projection only; Executive is not replaced:
- Item 1B — PIT/survivorship/selector evidence
- Item 6 — prospective counters and collector health
- Item 10 — evidence readiness for existing Monte Carlo; no duplicate Monte Carlo
- Item 11 — promotion readiness
- Item 12 — Gate BTC 2 / Evidence Factory state
- Item 13 — Strategy Factory -> Evidence Factory frozen handoff

A complete research pass terminates at `HUMAN_PROMOTION_REVIEW`.

## Deliberately excluded

EF-A6 autonomous orchestration is not activated. Full prospective autonomy is not claimed until the forward-only Stage 9 path has real admissible evidence. Dataset/economics readiness remains governed by existing Gate BTC 2 gates, including Issue #111.

## Immutable safety boundary

`RESEARCH_ONLY=true`
`SHADOW_ONLY=true`
`NOT_APPROVED=true`
`ENGINE_FEED=false`
`ORDERS=0`
`REAL_CAPITAL_BRL=0`
`NO_RETUNE=true`
`NO_BACKFILL=true`
`NO_SILENT_SOURCE_SUBSTITUTION=true`
`NO_AUTOMATIC_REAL_CAPITAL_PROMOTION=true`

## Acceptance

Tests must prove deterministic handoff, fail-closed missing evidence, negative-result permanence, no backfill/source substitution, authority reuse, shared Supervisor ownership, missing Stage 9 forward capture => `COLLECT_MORE`, and full pass => `HUMAN_PROMOTION_REVIEW` with zero engine/orders/capital.
