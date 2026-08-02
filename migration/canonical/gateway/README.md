# Canonical Gateway v0.10

This directory preserves the exact Gateway source admitted from
`qos_master_pipeline_v1_3_RECONCILED_FULLSET_READY.zip`.

## Provenance

- source package SHA-256: `f861fc31461a39713d98f4d4ad4c7aa9468df8fa9744e2eab1fb084ef4d8cf89`
- canonical subtree: `qos_master_pipeline_v1_3/qos_v2a1_gateway_scanner_v0_10`
- entrypoint: `scripts/00_run_all_v2a1.py`
- entrypoint SHA-256: `835e4ecb118c3ba2796c4e74c39a9025351b14415a2ddd1efb5465b82a724a20`
- version: `QOS_V2A1_GATEWAY_SCANNER_0.10`
- source mode: public market data, no API key, no account and no orders

The byte-preserving source archive is stored in ordered Base64 chunks under
`payload/gateway_v010_canonical_source.zip.b64.part-*`. Concatenating those
chunks produces `gateway_v010_canonical_source.zip.b64`; decoding it produces a
19,542-byte deterministic ZIP with SHA-256
`d90c140b18792bffb147f62fdaf2b5245437637ef2f59f21bbdf68435df01d54`.
Every decoded member is checked against the hashes frozen in the 2026-08-02
admission manifest before import or execution. The generated aggregate Base64
file is deliberately not tracked, preventing an incomplete materialization from
being mistaken for canonical evidence.

## Frozen reference replay

`tools/gateway_frozen_replay.py` verifies the exact source and the admitted
2026-08-02 reference payload, then:

1. verifies archive integrity, sizes and SHA-256 values;
2. verifies the exact README, requirements, manual watchlist and entrypoint;
3. replays deterministic portfolio construction from the admitted minimal
   `scanner_top500_features` snapshot;
4. compares all 118 strategy-selection rows, 132 composition rows, eight
   execution profiles, 80 Delta stop-rule rows and 80 decision-log rows;
5. runs the canonical offline fixture and validates the Gateway output contract;
6. emits TXT, JSON and ZIP evidence while preserving `RESEARCH_ONLY`, zero
   orders, zero real capital and `NOT_APPROVED`.

The replay deliberately does not reconstruct public-source acquisition or
feature generation because the admitted output package did not contain a
complete raw-history input snapshot. That boundary is explicit and fail-closed.
No formula, weight, threshold, stop, strategy or selection rule is changed.

For a local manual replay, materialize the aggregate source payload first:

```bash
cat migration/canonical/gateway/payload/gateway_v010_canonical_source.zip.b64.part-* \
  > migration/canonical/gateway/gateway_v010_canonical_source.zip.b64
GATE_BTC_RESEARCH_ONLY=true python tools/gateway_frozen_replay.py \
  --output-dir artifacts/gateway_v010_replay
rm migration/canonical/gateway/gateway_v010_canonical_source.zip.b64
```

GitHub Actions performs this materialization in its ephemeral workspace and
retains only the generated replay evidence artifact.
