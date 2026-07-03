# QRDS/QOS Canonical Data Collection Dry Run

Sprint 10A opens Phase 10 with a dry-run-only canonical data collection queue.

It records:

- target rows per symbol;
- observed canonical rows;
- gap rows;
- expected output paths;
- required canonical OHLCV fields;
- source profile;
- research-only safety lock.

Primary launcher:

```bash
bash qrds_canonical_data_collection_dry_run_serve.sh
```

Generated portal:

```text
crypto_decision_lab/artifacts/canonical_data_collection_dry_run/index.html
```

This dry run does not download data, connect accounts, or create live workflow markers.
