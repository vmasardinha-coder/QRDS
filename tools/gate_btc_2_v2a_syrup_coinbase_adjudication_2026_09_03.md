# GATE BTC 2.0 — SYRUP / Coinbase source adjudication

Date: 2026-09-03
Issue: #111
Scope: read-only source adjudication after preregistration #433 and physical qualification #437.

## Evidence authority

- Provider: Coinbase Exchange
- Market: Spot
- Pair: `SYRUP-USD`
- Frozen V2A identity: SYRUP / `maple-finance`
- Physical qualification workflow run: `33720708618`
- Immutable artifact: `gate-btc-2-v2a-syrup-coinbase-qualification`
- Artifact digest: `sha256:1822dc0dec8218397e156092d9bbe181abddcbcaa38f01558de51956c4e92398`
- Physical rows: 539 daily candles
- Observed interval: 2025-03-13 through 2026-09-02 UTC
- Boundary rows excluded deterministically: 2; raw responses remain hash-preserved
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

System 8 remains PARTIAL and Dataset Seal #111 remains DATA_BLOCKED. This checkpoint reduces source-path uncertainty for SYRUP only. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE`; Systems 10→14 remain dependency-bound; System 15 continues independently.
