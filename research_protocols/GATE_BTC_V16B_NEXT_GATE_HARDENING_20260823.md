# V16B next-gate hardening — 2026-08-23

Scope: reporting/orchestration only. No economic methodology, ranking, universe, sizing, costs, execution economics, promotion logic, orders, or capital changes.

## Canonical next window
- SIGNAL: 2026-08-27
- ENTRY: 2026-08-28
- COMPLETE EXIT: 2026-09-04
- completed canonical cycles before this window: 0

## Mandatory preflight
Run D-2 and D-1 checks before the canonical SIGNAL window and require all evidence families to be present and QA-valid:
- CMC Top-150 raw snapshot
- adjacent provenance/availability manifest + SHA256
- Binance shortability
- executability
- Binance funding
- price archives
- frozen signal/entry builders and dual-rank validators
- canonical publisher destination and hash/seal validator

## Rehearsal
Run the isolated one-day rehearsal from PR #82 before 2026-08-27. Rehearsal artifacts must retain:
- REHEARSAL=true
- PROSPECTIVE_COUNT=0
- CANONICAL_LEDGER=false
- ENGINE_FEED=false
- ORDERS=0
- REAL_CAPITAL=0

A rehearsal PASS is orchestration evidence only.

## Watchdogs
Immediately after the SIGNAL deadline, verify that the canonical SIGNAL seal exists, is causal, has a valid timestamp and SHA256, and references all required source evidence. If not, mark RED immediately and fail closed.

On ENTRY day, require a valid prior canonical SIGNAL seal before ENTRY can be recorded. After the ENTRY deadline, verify the canonical ENTRY seal with the same timestamp/hash/provenance checks.

## Reporting fields
Collection Health / Executive should expose:
- V16B_PREFLIGHT
- V16B_REHEARSAL
- SIGNAL_SEAL
- ENTRY_SEAL
- CANONICAL_CYCLE_COUNT
- NEXT_CANONICAL_EVENT

## QMASTER
Verify the local discovery path used by the Daily Executive so an existing canonical QMASTER artifact is discoverable. Until fixed, WARN_INPUT_GAP is a reporting defect, not a collection failure.

## Safety
RESEARCH_ONLY=true
SHADOW_ONLY=true
NOT_APPROVED=true
ENGINE_FEED=false
ORDERS=0
REAL_CAPITAL=0
NO_BACKFILL=true
NO_LATE_SEAL=true
NO_RETUNING=true
