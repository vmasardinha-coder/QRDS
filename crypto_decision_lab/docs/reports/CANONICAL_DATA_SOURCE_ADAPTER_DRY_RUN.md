# QRDS/QOS Canonical Data Source Adapter Dry Run

Sprint 10B maps the 10A dry-run collection queue into source-adapter options.

It validates:

- dry-run-only behavior;
- no network operation in this report;
- auth-free source adapter definitions;
- one adapter-job matrix per collection job;
- carry-forward of dataset depth gap;
- research-only policy lock.

Primary launcher:

```bash
bash qrds_canonical_data_source_adapter_dry_run_serve.sh
```

Generated portal:

```text
crypto_decision_lab/artifacts/canonical_data_source_adapter_dry_run/index.html
```

This report performs no network operation and does not create live workflow markers.
