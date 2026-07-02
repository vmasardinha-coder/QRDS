# QRDS/QOS — Dataset Evidence Scanner v1

Sprint 9K adds a local structured-dataset scanner for the Gate BTC research stack.

It scans offline/cache/fixture locations for CSV, JSON, JSONL, and NDJSON files that match the requested symbols. It records row counts, sample nulls, duplicate rows, time-column evidence, time-gap samples, and SHA-256 lineage.

This layer is research-only. It cannot generate execution instructions, allocation outputs, exchange access, or live-capital workflows.

## Commands

```bash
cd /workspaces/QRDS
bash qrds_dataset_evidence_scan.sh --output-dir artifacts/dataset_evidence_scan --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Serve:

```bash
cd /workspaces/QRDS
bash qrds_dataset_evidence_scan_serve.sh --output-dir artifacts/dataset_evidence_scan --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Codespaces:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```
