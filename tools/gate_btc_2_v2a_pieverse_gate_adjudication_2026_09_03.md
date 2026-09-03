# GATE BTC 2.0 — PIEVERSE / Gate source adjudication

Date: 2026-09-03
Issue: #111
Authority: preregistration #452 + physical qualification #467

## Physical evidence

- provider: Gate Spot
- pair: `PIEVERSE_USDT`
- canonical asset: Pieverse / `pieverse`
- physical qualification outcome: PASS
- admitted physical rows: 293 daily candles
- observed interval: 2025-11-14 through 2026-09-02 UTC
- duplicate rows: 0
- internal missing days: 0
- boundary rows excluded: 0
- monotonic timestamps: true
- `qa_pass=true`
- identity SHA-256: `2acc1ab7c19a36c6a32b7fec403bfa1378461e177fa7613d8d523109849843b7`
- raw candle page SHA-256: `6e692ca68b849fb45c25361b2a9660e28746f24ccf72b2eab8db45182f323ee2`
- immutable workflow artifact digest: `sha256:46714deb714e89acdd459953b6b896187e4b7dd1d16d9d61d6155119b25ec76e`

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
