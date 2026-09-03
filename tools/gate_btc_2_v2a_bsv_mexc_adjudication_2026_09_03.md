# GATE BTC 2.0 — BSV / MEXC source adjudication

Date: 2026-09-03
Issue: #111
Scope: read-only source adjudication after preregistration #422 and physical qualification #425.

## Evidence authority

- Provider: MEXC
- Market: Spot
- Pair: `BSVUSDT`
- Frozen V2A identity: BSV / `bitcoin-cash-sv`
- Physical qualification workflow run: `33701140056`
- Immutable artifact: `gate-btc-2-v2a-bsv-mexc-qualification`
- Artifact digest: `sha256:80ed8ac8f35c524f893ddaff0b022061bbfae7fa4ab858a4123ce6133782b3bd`
- Raw response rows: 500 daily candles
- In-window physical rows: 499 daily candles
- Observed interval admitted: 2025-04-22 through 2026-09-02 UTC
- Out-of-window boundary rows excluded deterministically: 1 (`2026-09-03`); raw response remains hash-preserved
- Duplicate rows: 0
- Internal missing days: 0
- Monotonic: true
- `qa_pass=true`
- Historical coverage sufficiency: NOT ASSERTED.

## Adjudication

`QUALIFIED_EXACT_SOURCE / PROSPECTIVE_COLLECTION_ONLY`

This source may be used only as a qualified exact source for future/prospective collection under the applicable frozen source contract. The qualification does not retroactively repair any prior PIT snapshot, survivorship defect or V2A historical gap and does not earn scientific or prospective evidence credit by itself.

## Explicit non-effects

- `dataset_sealed=false`
- `scientific_credit=false`
- `prospective_credit=false`
- `retroactive_v2a_repair_allowed=false`
- `historical_coverage_sufficiency_asserted=false`
- no V2A backfill
- no counter reset
- no denominator/universe change
- no retune
- no source substitution into frozen historical evidence
- no economics unlock
- no engine feed
- orders=0
- real capital=0

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

## Roadmap effect

System 8 remains PARTIAL and Dataset Seal #111 remains DATA_BLOCKED. This checkpoint reduces source-path uncertainty for BSV only. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE`; Systems 10→14 remain dependency-bound; System 15 continues independently.