# GATE BTC local retirement runbook

Status: RESEARCH_ONLY / NOT_APPROVED. This runbook retires only duplicated collection and reporting routines. It does not authorize trading, real capital, private credentials, or methodology changes.

## Minimum migration gate

Do not disable any Windows or Google routine until all items below are true for `main`:

1. A run triggered by `schedule` completes with `PASS` or `PASS_WITH_DATA_WARNINGS`.
2. V2A, Delta, Gateway upstream and Gateway downstream are all `PASS`.
3. The artifact contains `GATE_BTC_SHADOW_DELIVERY_REQUEST.json` bound to the run ID, attempt, head SHA and data cutoff.
4. Exactly three Shadow PDFs are generated and a `gate-btc-shadow-delivery-receipt-v1` receipt validates their filenames, sizes and SHA-256 hashes.
5. `RESEARCH_ONLY=True`, orders=0, capital=0 and `NOT_APPROVED` remain unchanged.

Recommended hardening: observe two consecutive automatic cycles before permanent removal. One validated automatic cycle is the minimum established gate; the second cycle reduces scheduler and transient-source risk.

## Routines eligible for retirement after the gate

Retire only local tasks that are exact duplicates of the migrated daily workflow:

- public-data V2A collection and frozen handoff;
- public-data Delta collection and frozen handoff;
- Gateway public capture/offline replay and downstream reference check;
- generation of the three daily Shadow reports from the same admitted handoff;
- duplicate Google upload or forwarding steps whose sole purpose is carrying those same artifacts.

## Routines that must remain active

Do not retire these unless they receive a separate migration and evidence package:

- `GATE_BTC_COLLECTION_COORDINATOR` and the prospective D50 seven-snapshot qualification campaign;
- any MacroQuant routine, which remains in standby and separate from GATE BTC;
- user portfolio, exchange, custody, API, copy-trade or operational routines;
- local emergency/manual collection used for failover until the rollback window ends;
- any Google routine that supplies unique data rather than duplicating GitHub output.

## Retirement procedure

1. Export the Windows Task Scheduler definitions and Google routine configuration.
2. Record task names, executable paths, schedules and last successful run in a TXT evidence file.
3. Disable, do not delete, the duplicated tasks.
4. Keep the disabled definitions for seven daily cycles.
5. Confirm GitHub schedule, artifact and three-report receipt on each cycle.
6. Delete only after seven cycles without fallback to local execution and after explicit user approval.

## Rollback

Re-enable the exported local tasks if any of the following occurs:

- no primary or fallback GitHub run for the expected cutoff;
- technical failure, stale cutoff, incomplete HTTP replay or missing component evidence;
- missing or invalid delivery request/receipt;
- fewer or more than exactly three official PDFs;
- any change to research-only, order, capital or operational locks.

Rollback does not permit operational execution. It restores only the previous research collection redundancy.
