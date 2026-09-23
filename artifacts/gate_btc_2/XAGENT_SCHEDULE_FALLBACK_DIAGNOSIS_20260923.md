# XAGENT schedule fallback diagnosis — 2026-09-23

## Observed fault
- Primary workflow: `gate-btc-xagent-disagree-transform.yml`.
- Frozen primary cadence: hourly at minute 37 UTC.
- Last successful XAGENT collection before diagnosis: 2026-09-23T15:38:35Z.
- No XAGENT scheduled run was present in the 2026-09-23T16:30:00Z..17:20:00Z schedule window, while other repository schedules were executing.
- Read-only freshness watchdog at 2026-09-23T17:28:35Z classified F-XAGENT-DISAGREE as `STALE_WARNING`, not `HARD_STALE`.

## Mechanical repair
Add a stale-only dispatch fallback using the repository's existing schedule-guard mechanism. The fallback may dispatch one current-time XAGENT run only when there is no active run and no successful target run within 5400 seconds (90 minutes).

## Scientific boundary
This is not backfill and does not recreate a missed timestamp. It does not alter the frozen transform, inputs, thresholds, direction, lookbacks, exposure mapping, economic outcomes, scientific credit, survivor credit, promotion authority, engine feed, orders, real capital, H1/H31, or canonical 580.
