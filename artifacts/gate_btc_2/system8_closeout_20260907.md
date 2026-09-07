# GATE BTC 2.0 — System 8 closeout

Date: 2026-09-07

## Decision

System 8 is closed as a blocking build stage and transitions to continuous prospective collection under the existing fail-closed research-only controls.

## Closure evidence

- PR #602 preregistered exact-source QA for the 91 legacy-loaded symbols.
- PR #605 physically qualified the frozen Legacy91 partition and preserved failures fail-closed.
- PRs #606–#614 resolved materially distinct residual source routes without silent substitution.
- PR #615 materialized the complete qualified registry with exactly 137 eligible sources and 13 structural exclusions preserved.
- PR #616 activated registry-driven prospective point-in-time collection and the D0 chain.
- PRs #617–#620 preregistered, physically qualified and admitted MEXC replacements for the four Bybit transport-inaccessible sources HTX/KAS/KCS/MNT.
- PR #621 aligned the PIT publisher with the canonical ledger schema after the isolated 137/137 physical run.
- Canonical runtime `runtime/data_quality/v2a/STATUS.json` now records:
  - `latest_attempted_symbols = 137`
  - `latest_loaded_symbols = 137`
  - `latest_failed_symbols = 0`
  - `latest_coverage_ratio = 1.0`
  - `snapshot_count = 1`
  - `prospective_point_in_time_universe_observed = true`
  - `future_point_in_time_only = true`
  - `retrospective_backfill_allowed = false`
  - `status = ACTIVE_RESEARCH_ONLY`

The first credited post-cutover PIT observation is therefore present and D0 has started.

## Frozen safety boundary

This closeout changes no scientific method, universe rule, threshold, economics, historical evidence, or strategy approval state.

The following remain mandatory:

- `RESEARCH_ONLY = true`
- `SHADOW_ONLY = true`
- `NOT_APPROVED = true`
- `ENGINE_FEED = false`
- `ORDERS = 0`
- `REAL_CAPITAL = 0`
- no retrospective backfill
- no counter reset
- no retune
- no silent source substitution
- fail closed on incomplete PIT collection

## Operational consequence

System 8 is no longer the critical-path blocker. Its job is now to accumulate new forward-only PIT observations automatically. Any future collection failure is an operational incident to repair under the same frozen contracts; it does not reopen historical reconstruction or permit backfill.

Next critical-path focus: System 9 / Stage 9 forward evidence accumulation and its existing `COLLECT_MORE_FORWARD_EVIDENCE` gate.