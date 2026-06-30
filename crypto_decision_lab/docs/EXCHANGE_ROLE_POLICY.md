# Exchange Role Policy

## Roles

### Binance — `SIMULATION_FIXTURE_REPLAY`

- Simulation, fixtures, benchmark, and replay only.
- No live HTTP calls.
- No API key.
- Not a real execution account.
- Approved: Sprint 4K.

### OKX — `PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH`

- Public HTTP candles and ticker only.
- No API key, no account, no orders.
- Approved: Sprint 4Q (live smoke PASS).

### Bybit — `PENDING_BLOCKED_BY_403`

- All public endpoints returned 403 in Codespaces environment.
- Intended as future real-base candidate alongside OKX.
- Blocked pending remediation. See `BYBIT_403_BACKLOG.md`.

## Promotion policy

A role may only be promoted (e.g. Bybit from PENDING to PUBLIC_HTTP_LIVE) after:

1. A dedicated gate sprint that tests the new capability.
2. All tests in `tests/safety/` continue to pass.
3. The sprint result is documented in `docs/gates/sprint_gate_log.md`.
