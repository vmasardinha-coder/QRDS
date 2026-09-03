# GATE BTC 2.0 — REAL / MEXC source adjudication

Date: 2026-09-03
Issue: #111
Authority: preregistration #452 + physical qualification #468

## Physical evidence

- provider: MEXC Spot
- pair: `REALUSDT`
- canonical asset: REAL / `reallink`
- physical qualification workflow run: `33745135482`
- immutable workflow artifact: `gate-btc-2-v2a-real-mexc-qualification`
- immutable workflow artifact digest: `sha256:d1846b067a0e324a652d98ec7cbf69918f8c2c0ddb9820531751691369d369c9`
- physical qualification outcome: PASS
- `qa_pass=true`
- qualification-time `admission_scope=NONE`
- scientific credit: false
- prospective credit: false
- historical coverage sufficiency: NOT ASSERTED

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This adjudication qualifies only the exact preregistered public MEXC Spot `REALUSDT` route for future/prospective collection under the frozen V2A source contract. It does not retroactively repair any prior PIT snapshot, survivorship defect or historical V2A gap, and physical qualification by itself earns zero scientific, prospective-epoch or D0 credit.

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
