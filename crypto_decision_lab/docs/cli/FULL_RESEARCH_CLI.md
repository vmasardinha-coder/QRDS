# QRDS Full Research CLI

## Purpose

Sprint 7C adds an offline full-chain CLI runner.

It runs:

```text
OKX fixture
↓
public adapter
↓
cache
↓
research pipeline
↓
walk-forward
↓
baseline model
↓
hypothetical backtest skeleton
↓
edge report
↓
edge report export
↓
integration health report
```

## Command from repository root

```bash
cd /workspaces/QRDS

bash qrds_full_research.sh \
  --output-dir artifacts/full_research \
  --run-id full-research-run \
  --report-id edge-report
```

## Direct Python command from project directory

```bash
cd /workspaces/QRDS/crypto_decision_lab

python -m crypto_decision_lab.cli.full_research \
  --output-dir artifacts/full_research \
  --run-id full-research-run \
  --report-id edge-report
```

## Outputs

```text
full_research_summary.json
integration_health_report.json
contract_freeze_registry.json
edge_console_summary.json
edge_exports/<report-id>/edge_report.json
edge_exports/<report-id>/edge_summary.json
edge_exports/<report-id>/edge_export_index.json
```

## Safety

This CLI is offline and research-only.

It does not:
- connect to an account
- require an API key
- generate orders
- use real capital
- generate executable trading signals
- produce recommendations
