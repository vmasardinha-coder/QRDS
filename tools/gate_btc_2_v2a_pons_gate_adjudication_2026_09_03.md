# GATE BTC 2.0 — PONS / Gate source adjudication

Date: 2026-09-03
Replacement Dataset Epoch: #455
Authority: preregistration #452 + physical qualification #471

## Physical evidence

- provider: Gate Spot
- pair: `PONS_USDT`
- canonical asset: PONS / `pons`
- physical qualification workflow run: `33745173606`
- immutable workflow artifact: `gate-btc-2-v2a-pons-gate-qualification`
- immutable workflow artifact digest: `sha256:87b33e78f3153eab63be6260f46bdde3561c439618f68b31e86ff56322fca845`
- physical qualification outcome: PASS
- admitted physical rows: 7 daily candles
- observed interval: 2026-08-27 through 2026-09-02 UTC
- boundary rows excluded: 0
- duplicate rows: 0
- internal missing days: 0
- monotonic timestamps: true
- `qa_pass=true`
- identity SHA-256: `aa35c6cd67b1433740c49b29524475d7e04204addac22bde33a75e2b8d950305`
- raw candle page SHA-256: `cb04c3962296842c002f4b5e5fbaafffab4bc6bfe11ccfdaff16eb381aac789a`
- qualification-time `admission_scope=NONE`
- scientific credit: false
- prospective credit: false
- historical coverage sufficiency: NOT ASSERTED

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This adjudication qualifies only the exact preregistered public Gate Spot `PONS_USDT` route for future/prospective collection under the frozen V2A source contract. The short observed history is preserved as evidence of the instrument's recent opening and is not treated as historical coverage sufficiency. It does not retroactively repair any prior PIT snapshot, survivorship defect or historical V2A gap, and physical qualification by itself earns zero scientific, prospective-epoch or D0 credit.

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
