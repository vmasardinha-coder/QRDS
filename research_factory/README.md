# QRDS Research Factory

Persistent orchestration layer for autonomous research products. This namespace is intentionally isolated from active QRDS runtime, strategy, collector, reporting and prospective-ledger paths.

## Products

- `QRDS-DATA`: auditable data-gap diagnosis, ingestion contracts and causal derived-data products.
- `QRDS-LAB`: preregistered discovery, falsification and independent replication for OPEN_DISCOVERY tracks only.
- `QRDS-VALIDATE`: freeze/handoff contracts for new replicated survivors; never mutates existing prospective clocks.
- `QRDS-GUARD`: non-interference and transition policy.
- `QRDS-REPORT`: factory-state/report contracts consuming read-only evidence.

## Safety boundary

The factory treats every active/frozen/prospective/shadow track as read-only. It must not change existing workflows, schedules, runtime pointers, ledgers, parameters, costs, calendars, counters, hashes, collectors or canonical reports. B3/H1 and B3 specialist discovery remain externally owned and are integrated by read-only status references only.

Global invariants: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ORDERS=0`, `REAL_CAPITAL=0`, `ENGINE_FEED=false`, no blind-holdout peeking, no backfill, no survivor retuning.

## State flow

`DATA_BLOCKED -> data-gap resolution -> OPEN_DISCOVERY -> preregister -> test -> falsify/replicate -> CLOSED_NULL or survivor freeze -> handoff -> SURVIVOR_MONITORING/FROZEN_PROSPECTIVE`

Transitions are fail-closed and append-only where evidence history is involved. Existing track state is never rewritten by this namespace.