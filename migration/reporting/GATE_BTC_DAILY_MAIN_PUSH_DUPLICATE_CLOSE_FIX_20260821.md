# GATE BTC — Daily main-push duplicate-close fix

Status: RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED
Orders: 0
Real capital: 0

## Incident
On 2026-08-21, a main-branch merge after the scheduled Daily collection triggered `GATE BTC Daily Research Collection` again through the `push` trigger added by PR #72. The workflow resolves the most recent completed UTC close (`today UTC - 1 day`). The LOCK valuation runtime ledger had already consumed that close earlier in the scheduled run, so the fail-closed sidecar correctly rejected the duplicate date because it expected the next consecutive close.

This caused the upstream Daily workflow to fail and downstream workflow_run consumers to fail closed as designed. No scientific counter may advance from those failed runs.

## Fix
Remove `main` from the Daily workflow `push` branch list, restoring collection authority to:
- scheduled Daily runs;
- explicit workflow_dispatch when a valid completed close is intentionally requested;
- pull_request validation for code changes;
- the legacy migration agent branch push path.

This does not weaken the LOCK consecutive-close guard and does not create idempotent synthetic closes. The next scheduled Daily naturally runs the newest main code against the next completed UTC close.

## Scientific boundary
No methodology, selection, costs, parameters, signals, counters, backfill policy, orders or capital are changed. Failed 2026-08-21 post-merge runs remain ineligible evidence.
