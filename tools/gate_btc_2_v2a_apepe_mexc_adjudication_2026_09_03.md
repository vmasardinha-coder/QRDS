# GATE BTC 2.0 — APEPE / MEXC source adjudication

Date: 2026-09-03
Issue: #111
Authority: preregistration #452 + physical qualification #469

## Physical evidence

- provider: MEXC Spot
- pair: `APEPEUSDT`
- canonical asset: APEPE / `ape-and-pepe`
- physical qualification workflow run: `33745147696`
- immutable workflow artifact: `gate-btc-2-v2a-apepe-mexc-qualification`
- immutable workflow artifact digest: `sha256:79a40a81b9c70bb5dbb58a08f4f64d9077412181f34a2a485a78f0b7ca5f8169`
- physical qualification outcome: PASS
- admitted physical rows: 499 daily candles
- observed interval: 2025-04-22 through 2026-09-02 UTC
- boundary rows excluded deterministically: 1; raw response remains hash-preserved
- duplicate rows: 0
- internal missing days: 0
- monotonic timestamps: true
- `qa_pass=true`
- identity SHA-256: `79815605e8338d5fd9ad5ce412fc5e2062f4955c41c328c46f65686e91f5e4bc`
- raw candle page SHA-256: `90148652f8d89f8a366d95fd6ee2586f4d6267a310191b21c37f9fc522d5487b`
- qualification-time `admission_scope=NONE`
- scientific credit: false
- prospective credit: false
- historical coverage sufficiency: NOT ASSERTED

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This adjudication qualifies only the exact preregistered public MEXC Spot `APEPEUSDT` route for future/prospective collection under the frozen V2A source contract. It does not retroactively repair any prior PIT snapshot, survivorship defect or historical V2A gap, and physical qualification by itself earns zero scientific, prospective-epoch or D0 credit.

No backfill, source stitching, counter reset, denominator/universe change, retune, economics, engine feed, orders or capital is authorized. The original historical Dataset Seal remains terminal negative evidence and is not reopened.

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

System 8 remains `PROSPECTIVE_EPOCH_WAITING_CUTOVER_GATE`; D0 remains unset until the frozen complete causal post-preregistration V2A cutover gate passes. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE` under its independent clock. Systems 10–14 remain dependency-bound; System 15 remains independent; System 16 remains future-controlled.
