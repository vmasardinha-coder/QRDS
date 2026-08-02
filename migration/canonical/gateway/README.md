# Canonical Gateway v0.10

This directory preserves the exact Gateway source admitted from
`qos_master_pipeline_v1_3_RECONCILED_FULLSET_READY.zip`.

## Provenance

- source package SHA-256: `f861fc31461a39713d98f4d4ad4c7aa9468df8fa9744e2eab1fb084ef4d8cf89`
- canonical subtree: `qos_master_pipeline_v1_3/qos_v2a1_gateway_scanner_v0_10`
- entrypoint: `scripts/00_run_all_v2a1.py`
- version: `QOS_V2A1_GATEWAY_SCANNER_0.10`
- source mode: public market data, no API key, no account and no orders

The byte-preserving source archive is stored as
`gateway_v010_canonical_source.zip.b64`. The decoded deterministic ZIP hash is
`d90c140b18792bffb147f62fdaf2b5245437637ef2f59f21bbdf68435df01d54`.
Every decoded member is checked against the hashes frozen in the 2026-08-02
admission manifest before import or execution.

## Frozen reference replay

`tools/gateway_frozen_replay.py` materializes the exact source and the admitted
2026-08-02 reference payload, then:

1. verifies archive integrity, sizes and SHA-256 values;
2. verifies the exact README, requirements, manual watchlist and entrypoint;
3. replays deterministic portfolio construction from the frozen
   `scanner_top500_features.csv`;
4. compares all 118 strategy-selection rows, 132 composition rows, eight
   execution profiles, 80 Delta stop-rule rows and 80 decision-log rows;
5. runs the canonical offline fixture and validates the Gateway output contract;
6. emits dated-style TXT, JSON and ZIP evidence while preserving
   `RESEARCH_ONLY`, zero orders, zero real capital and `NOT_APPROVED`.

The replay deliberately does not reconstruct the public-source acquisition or
feature-generation stage because the admitted output package did not contain a
complete raw-history input snapshot. That boundary is explicit and fail-closed.
No formula, weight, threshold, stop, strategy or selection rule is changed.

```bash
GATE_BTC_RESEARCH_ONLY=true python tools/gateway_frozen_replay.py \
  --output-dir artifacts/gateway_v010_replay
```
