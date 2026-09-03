# GATE BTC 2.0 — AKE / MEXC source adjudication

Date: 2026-09-03
Issue: #111
Authority: preregistration #440 + physical qualification #443

## Physical evidence

- provider: MEXC Spot
- pair: `AKEUSDT`
- canonical asset: Akedo / `akedo`
- physical qualification outcome: PASS
- admitted physical rows in qualification artifact: 378 daily candles
- observed interval: 2025-08-21 through 2026-09-02 UTC
- duplicate rows: 0
- internal missing days: 0
- monotonic timestamps: true
- `qa_pass=true`
- artifact digest: `sha256:52aca2fdd8f52ec58fd4a803f0a9fa8ef92f67409e94eeaded138f6497aa4c12`

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This adjudication qualifies only the exact public source identity and forward collection path. It does not assert historical coverage sufficiency and does not repair any prior PIT observation, survivorship defect or frozen V2A snapshot.

No historical backfill, source stitching, counter reset, scientific credit, prospective evidence credit, denominator/universe change, retune, economics, engine feed, orders or capital is authorized.

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

System 8 / Dataset Seal #111 remains blocked pending the independent historical readiness contract. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE`.
