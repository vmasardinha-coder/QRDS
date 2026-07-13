# Phase 198 - Data Quality Anomaly Audit

**Status:** `PASS_RESEARCH_ONLY`

## Summary

- Registered sources: `9`
- Inspected sources: `9`
- Flagged sources: `1`
- Duplicate records: `0`
- Missing values: `1`
- OHLC invariant violations: `2`
- Negative volume rows: `1`
- Missing symbols: `0`
- Large time gaps: `0`

## Source audit

| Source | Inspection | Rows | Duplicates | Missing | OHLC | Gaps | Flags | Path |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `src_88ca3e1775fc4afc` | `PARSED` | 5 | 0 | 1 | 2 | 0 | 4 | `data/fixtures/dql_corrupted_candles.json` |
| `src_eca8177c0504a0cd` | `PARSED` | 10 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/dql_sample_candles.json` |
| `src_1c290bf66dc79372` | `PARSED` | 1 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json` |
| `src_1a97b32a5ffae468` | `PARSED` | 1 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/okx_public/okx_public_eth_usdt_1h_sample.json` |
| `src_a6182ce795bd1e58` | `PARSED` | 1 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/okx_public/okx_public_sol_usdt_1h_sample.json` |
| `src_2b37024a808386cb` | `PARSED` | 12 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/research/btc_usdt_1h_bull.json` |
| `src_fed4741f39224814` | `PARSED` | 12 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/research/btc_usdt_1h_crash.json` |
| `src_0f21a8ca6712b293` | `PARSED` | 12 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/research/btc_usdt_1h_neutral.json` |
| `src_0d6b121587e4554b` | `PARSED` | 12 | 0 | 0 | 0 | 0 | 0 | `data/fixtures/research/btc_usdt_1h_stress.json` |

Findings are descriptive. Zero detected anomalies does not establish data trust.

```text
operational_status: BLOCKED_RESEARCH_ONLY
anomaly_audit_ready: True
anomaly_free_validated: False
data_trust_validated: False
decision_layer_allowed: False
canonical_data_writes: 0
```

Next: `PHASE_199_SOURCE_RECONCILIATION_PROVENANCE_SCORE_RESEARCH_ONLY`
