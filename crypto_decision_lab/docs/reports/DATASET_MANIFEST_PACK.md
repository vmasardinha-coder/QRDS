# QRDS/QOS — Dataset Manifest Pack v1

Sprint 9E creates explicit per-symbol research dataset manifests for the Gate BTC evidence stack.

It is research-only. It cannot unlock trading, allocation, order generation, exchange connectivity, or live-fund workflows.

## Purpose

The prior Data Audit Evidence Pack showed that dataset manifests were missing. This sprint creates a manifest packet for each requested symbol and records the remaining gaps:

- local source file lineage;
- explicit dataset row counts;
- explicit walk-forward split counts;
- upstream evidence score;
- artifact hashes and traceability.

## Usage

```bash
cd /workspaces/QRDS
bash qrds_dataset_manifest_from_stack_serve.sh
```

Open the printed Codespaces port.
