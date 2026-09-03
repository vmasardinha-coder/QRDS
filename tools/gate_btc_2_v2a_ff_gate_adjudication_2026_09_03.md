# GATE BTC 2.0 — FF / Gate source adjudication

Date: 2026-09-03
Issue: #111
Authority: preregistration #445 + physical qualification #450

## Physical evidence

- provider: Gate Spot
- pair: `FF_USDT`
- canonical asset: Falcon Finance / `falcon-finance-ff`
- physical qualification outcome: PASS
- admitted physical rows: 339 daily candles
- observed interval: 2025-09-29 through 2026-09-02 UTC
- duplicate rows: 0
- internal missing days: 0
- boundary rows excluded: 0
- monotonic timestamps: true
- `qa_pass=true`
- artifact digest: `sha256:bfca72bbe1aded1e6ffb16081da3423ea4e8b2516098fc699742e17c966537c6`

The previously attempted Binance route remains immutable negative evidence (`HTTP 451` in #442). It is not overwritten or stitched into this source.

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This adjudication qualifies the exact public Gate source and future collection path only. Historical coverage sufficiency remains unasserted. The newly qualified source cannot repair prior point-in-time observations or remove survivorship bias from frozen historical snapshots.

No backfill, source stitching, counter reset, scientific/prospective evidence credit, denominator/universe change, retune, economics, engine feed, orders or capital is authorized.

## Safety

- RESEARCH_ONLY=true
- SHADOW_ONLY=true
- NOT_APPROVED=true
- ENGINE_FEED=false
- ORDERS=0
- REAL_CAPITAL_BRL=0
- NO_RETUNE=true
- NO_BACKFILL=true
- NO_COUNTER_RESET=true
- NO_SILENT_SOURCE_SUBSTITUTION=true
- FAIL_CLOSED=true

System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE` under its independent forward clock.
