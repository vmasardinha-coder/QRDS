# GATE BTC 2.0 — TIBBIR / MEXC source adjudication

Date: 2026-09-03
Replacement Dataset Epoch: #455
Authority: preregistration #452 + physical qualification #470

## Physical evidence

- provider: MEXC Spot
- pair: `TIBBIRUSDT`
- canonical asset: TIBBIR / `ribbita-by-virtuals`
- physical qualification workflow run: `33745159251`
- immutable workflow artifact: `gate-btc-2-v2a-tibbir-mexc-qualification`
- immutable workflow artifact digest: `sha256:0d5070d43dd89712975968ce75570edfbfbb550bfb9566d0b6cda696ce2fa686`
- physical qualification outcome: PASS
- admitted physical rows: 499 daily candles
- observed interval: 2025-04-22 through 2026-09-02 UTC
- boundary rows excluded deterministically: 1; raw response remains hash-preserved
- duplicate rows: 0
- internal missing days: 0
- monotonic timestamps: true
- `qa_pass=true`
- identity SHA-256: `58707ee477b2cb0b3b8de628a455cf7e0a5495ca557a015ca2ee7fca9fdc094c`
- raw candle page SHA-256: `999e9f83a0c1781f7da339c609cd9d566becb1957a246298819d651b55df3904`
- qualification-time `admission_scope=NONE`
- scientific credit: false
- prospective credit: false
- historical coverage sufficiency: NOT ASSERTED

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This adjudication qualifies only the exact preregistered public MEXC Spot `TIBBIRUSDT` route for future/prospective collection under the frozen V2A source contract. It does not retroactively repair any prior PIT snapshot, survivorship defect or historical V2A gap, and physical qualification by itself earns zero scientific, prospective-epoch or D0 credit.

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
