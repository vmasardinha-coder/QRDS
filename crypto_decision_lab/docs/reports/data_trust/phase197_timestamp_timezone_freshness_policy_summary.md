# Phase 197 - Timestamp, Timezone and Freshness Policy

**Status:** `PASS_RESEARCH_ONLY`

## Purpose

Apply a deterministic temporal policy to the Phase 196 source registry. The audit records timestamp fields, parsing modes, timezone evidence, ordering and descriptive freshness.

This phase does not certify data trust.

## Summary

- Registered sources: `9`
- Temporal candidates: `6`
- Inspected temporal sources: `6`
- Sources requiring timezone review: `0`
- Sources with invalid timestamps: `0`
- Sources with non-monotonic ordering: `0`
- Missing sources: `0`

## Policy

- Temporal data requires an explicit timestamp field.
- UTC or explicit offset is preferred.
- Naive timestamps are not accepted as final trust evidence.
- Epoch timestamps are interpreted as UTC with unit recorded.
- Monotonic ordering and duplicate timestamps must be audited.
- Fixture freshness is not operationally enforced.
- Research-input freshness is descriptive at this stage.

## Source audit

| Source | Inspection | Timezone | Freshness | Invalid | Non-monotonic | Path |
|---|---|---|---|---:|---:|---|
| `src_88ca3e1775fc4afc` | `INSPECTED` | `UTC_OR_OFFSET_EXPLICIT` | `FIXTURE_NOT_OPERATIONALLY_ENFORCED` | 0 | 0 | `data/fixtures/dql_corrupted_candles.json` |
| `src_eca8177c0504a0cd` | `INSPECTED` | `UTC_OR_OFFSET_EXPLICIT` | `FIXTURE_NOT_OPERATIONALLY_ENFORCED` | 0 | 0 | `data/fixtures/dql_sample_candles.json` |
| `src_1c290bf66dc79372` | `NON_TEMPORAL_NO_HINT` | `NOT_EVALUATED` | `NOT_EVALUATED` | 0 | 0 | `data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json` |
| `src_1a97b32a5ffae468` | `NON_TEMPORAL_NO_HINT` | `NOT_EVALUATED` | `NOT_EVALUATED` | 0 | 0 | `data/fixtures/okx_public/okx_public_eth_usdt_1h_sample.json` |
| `src_a6182ce795bd1e58` | `NON_TEMPORAL_NO_HINT` | `NOT_EVALUATED` | `NOT_EVALUATED` | 0 | 0 | `data/fixtures/okx_public/okx_public_sol_usdt_1h_sample.json` |
| `src_2b37024a808386cb` | `INSPECTED` | `UTC_OR_OFFSET_EXPLICIT` | `FIXTURE_NOT_OPERATIONALLY_ENFORCED` | 0 | 0 | `data/fixtures/research/btc_usdt_1h_bull.json` |
| `src_fed4741f39224814` | `INSPECTED` | `UTC_OR_OFFSET_EXPLICIT` | `FIXTURE_NOT_OPERATIONALLY_ENFORCED` | 0 | 0 | `data/fixtures/research/btc_usdt_1h_crash.json` |
| `src_0f21a8ca6712b293` | `INSPECTED` | `UTC_OR_OFFSET_EXPLICIT` | `FIXTURE_NOT_OPERATIONALLY_ENFORCED` | 0 | 0 | `data/fixtures/research/btc_usdt_1h_neutral.json` |
| `src_0d6b121587e4554b` | `INSPECTED` | `UTC_OR_OFFSET_EXPLICIT` | `FIXTURE_NOT_OPERATIONALLY_ENFORCED` | 0 | 0 | `data/fixtures/research/btc_usdt_1h_stress.json` |

## Safety

```text
operational_status: BLOCKED_RESEARCH_ONLY
temporal_policy_ready: True
data_trust_validated: False
freshness_validated: False
decision_layer_allowed: False
canonical_data_writes: 0
```

## Next

`PHASE_198_DATA_QUALITY_ANOMALY_AUDIT_RESEARCH_ONLY`
