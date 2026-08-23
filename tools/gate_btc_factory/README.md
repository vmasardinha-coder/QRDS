# QRDS Factory

Persistent, isolated orchestration layer for autonomous research products under the repository's existing GATE-approved tool namespace.

Products: QRDS-DATA, QRDS-LAB, QRDS-VALIDATE, QRDS-GUARD, QRDS-REPORT.

This namespace is read-only with respect to every active/frozen/prospective/shadow track. It must not alter workflows, schedules, runtime pointers, existing ledgers, parameters, costs, calendars, counters, hashes, collectors, canonical reports, B3/H1 or specialist-owned B3 discovery.

Global invariants: RESEARCH_ONLY=true; SHADOW_ONLY=true; NOT_APPROVED=true; ORDERS=0; REAL_CAPITAL=0; ENGINE_FEED=false; no blind-holdout peeking; no backfill; no frozen-survivor retuning.

State flow: DATA_BLOCKED -> data resolution -> OPEN_DISCOVERY -> preregister -> test -> falsify/replicate -> CLOSED_NULL or survivor freeze -> handoff -> SURVIVOR_MONITORING/FROZEN_PROSPECTIVE. All uncertain transitions fail closed.