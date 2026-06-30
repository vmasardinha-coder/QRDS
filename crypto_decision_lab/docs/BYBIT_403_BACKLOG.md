# Bybit 403 Backlog

## Status

```
PENDING_BLOCKED_BY_403
```

## History

- **Sprint 4I**: Bybit public HTTP smoke test — all endpoints returned `HTTP 403 Forbidden` in GitHub Codespaces.
- **Sprint 4J**: Bybit remediation sprint — multiple public endpoints tested, all returned 403. Environment/IP likely blocked by Bybit.
- **Sprint 4K**: Exchange role policy set — Bybit assigned `PENDING_BLOCKED_BY_403`.

## Intended future role

Bybit is intended as a real-base candidate alongside OKX for live public data once the 403 is resolved.

## Remediation checklist (future sprint)

- [ ] Test from non-Codespaces environment (local, VPS, different IP range)
- [ ] Try different Bybit public endpoints (v5 API)
- [ ] Add `User-Agent` and `Accept` headers if required
- [ ] Document which endpoints succeed
- [ ] Open a new gate sprint: `Sprint 4J-Remediation`
- [ ] Gate must pass before changing role to `PUBLIC_HTTP_LIVE_NO_AUTH`
- [ ] Create `bybit_public.py` (do not modify `bybit_public_pending.py`)
- [ ] Add `bybit` to integration tests

## What NOT to do

- Do not add Bybit authentication as a workaround.
- Do not use a proxy/VPN without an approved gate sprint.
- Do not remove `bybit_public_pending.py` — it must remain as a documented stub.
- Do not promote Bybit's role without a passing gate sprint.
