# CCXT standalone conclusion — 2026-09-21

Status: **CONCLUDED / COMPONENT_AUDITOR_NOT_ALPHA_SOURCE**

## What was proven
- Upstream pinned provenance: commit `6c98f320d87cab3fe2224a65bd293dd15673c31d`, Python release `4.5.81`.
- The unified capability surface is present across OKX, Kraken, and Coinbase for OHLCV, public trades, order books, create/cancel order.
- The installed release reports 104 supported exchanges.
- Exchange-specific differences remain material (rate limits, timeframe surfaces, venue semantics), so CCXT is an adapter layer rather than a scientific equivalence guarantee.

## Migration decision
- **No alpha family is migrated from CCXT.**
- No Factory strategy or scientific gate is added in this round.
- CCXT remains useful as a transport/source-normalization component for isolated external research and as a cross-venue source probe when Factory source qualification needs an additional public adapter.
- Any data admitted to Factory must still pass QRDS source qualification, PIT/causality, provenance, and fail-closed checks; a unified CCXT API is not evidence of semantic equivalence between venues.

## Permanent role
`COMPONENT / SOURCE_PROBE / TRANSPORT`, invoked when needed. It is not a hypothesis generator by itself.

`RESEARCH_ONLY=true`
`SHADOW_ONLY=true`
