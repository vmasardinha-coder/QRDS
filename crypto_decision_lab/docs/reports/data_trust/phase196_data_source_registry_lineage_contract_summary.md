# Phase 196 — Data Source Registry + Lineage Contract

**Status:** `PASS_RESEARCH_ONLY`

## Purpose

Create a deterministic, read-only registry of discovered research data and fixture files. Each source receives a stable identifier, content hash and lineage contract.

This phase does not validate data trust, freshness, anomaly absence, economic edge or operational readiness.

## Summary

- Scan roots: `2`
- Existing roots: `1`
- Missing roots: `1`
- Discovered files: `9`
- Verified SHA256 hashes: `9`
- Empty files: `0`
- Symlinks skipped: `0`
- Duplicate-content groups: `0`

## Scan roots

| Root | Status | Files discovered |
|---|---|---:|
| `data` | `PRESENT` | 9 |
| `tests/fixtures` | `MISSING` | 0 |

## Registered sources

| Source ID | Role | Format | Bytes | Fingerprint | Path |
|---|---|---|---:|---|---|
| `src_88ca3e1775fc4afc` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 662 | `d7a5cd8db49358dc` | `data/fixtures/dql_corrupted_candles.json` |
| `src_eca8177c0504a0cd` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 1231 | `1e7ec48436145a20` | `data/fixtures/dql_sample_candles.json` |
| `src_1c290bf66dc79372` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 2970 | `7872201da811ac46` | `data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json` |
| `src_1a97b32a5ffae468` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 3324 | `306c3a76d18b25b4` | `data/fixtures/okx_public/okx_public_eth_usdt_1h_sample.json` |
| `src_a6182ce795bd1e58` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 3256 | `9fbec33cf315519e` | `data/fixtures/okx_public/okx_public_sol_usdt_1h_sample.json` |
| `src_2b37024a808386cb` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 3463 | `e5f3ac7e321d3418` | `data/fixtures/research/btc_usdt_1h_bull.json` |
| `src_fed4741f39224814` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 3428 | `f2faec9060cf47a3` | `data/fixtures/research/btc_usdt_1h_crash.json` |
| `src_0f21a8ca6712b293` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 3539 | `9b0bdcc9f43a960a` | `data/fixtures/research/btc_usdt_1h_neutral.json` |
| `src_0d6b121587e4554b` | `TEST_FIXTURE` | `STRUCTURED_TEXT` | 3434 | `2e3d8707bf105db4` | `data/fixtures/research/btc_usdt_1h_stress.json` |

## Duplicate content evidence

- No duplicate content groups detected.

## Lineage contract

- Content SHA256 is mandatory.
- Inputs are treated as read-only evidence.
- Temporal datasets must use explicit timestamps.
- UTC is required when temporal semantics apply.
- Freshness is audited in Phase 197.
- Data anomalies are audited in Phase 198.
- Cross-source reconciliation is audited in Phase 199.
- Canonical writes remain prohibited.

## Safety

```text
operational_status: BLOCKED_RESEARCH_ONLY
data_trust_validated: False
shadow_decision_allowed: False
decision_layer_allowed: False
promotion_allowed: False
canonical_data_writes: 0
```

## Next

`PHASE_197_TIMESTAMP_TIMEZONE_FRESHNESS_POLICY_RESEARCH_ONLY`
