# GATE BTC 2.0 — AERO / Coinbase source adjudication

Date: 2026-09-02
Issue: #111
Scope: read-only source adjudication after preregistration #418 and physical qualification #420.

## Evidence authority

- Provider: Coinbase Exchange
- Market: Spot
- Pair: `AERO-USD`
- Frozen V2A identity: AERO / `aerodrome-finance`
- Physical qualification workflow run: `33689956505`
- Immutable artifact: `gate-btc-2-v2a-aero-coinbase-qualification`
- Artifact digest: `sha256:4ca45c5a124f648cafe11b1d2e27f0bf368d2893610c749833648c3068a282b2`
- Physical rows: 940 daily candles
- Observed interval: 2024-02-06 through 2026-09-02 UTC
- Duplicate rows: 0
- Internal missing days: 0
- Monotonic: true
- `qa_pass=true`
- Coinbase pagination boundary rows excluded deterministically: 3; raw responses remain hash-preserved.
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

System 8 remains PARTIAL and Dataset Seal #111 remains DATA_BLOCKED. This checkpoint reduces source-path uncertainty for AERO only. System 9 remains `COLLECT_MORE_FORWARD_EVIDENCE`; Systems 10→14 remain dependency-bound; System 15 continues independently.