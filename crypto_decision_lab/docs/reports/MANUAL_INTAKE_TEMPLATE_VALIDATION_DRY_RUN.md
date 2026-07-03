# QRDS/QOS Manual Intake Template / Validation Dry Run

Sprint 10C creates dry-run manual intake templates for canonical research datasets.

It validates:

- required canonical OHLCV fields;
- one template per symbol from the adapter queue;
- sample-row shape;
- artifact-only writes;
- zero writes into canonical data directories;
- research-only policy lock.

Primary launcher:

```bash
bash qrds_manual_intake_template_validation_dry_run_serve.sh
```

Generated portal:

```text
crypto_decision_lab/artifacts/manual_intake_template_validation_dry_run/index.html
```

This report writes templates under artifacts only. It does not ingest or download data.
