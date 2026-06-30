# QRDS Scenario Stress Pack

Sprint 8B adds descriptive stress scenarios to a multi-asset research report.

## Command from repository root

First generate a multi-asset report:

```bash
bash qrds_multi_asset_report.sh \
  --output-dir artifacts/multi_asset_report \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then generate stress pack:

```bash
bash qrds_scenario_stress.sh \
  --multi-asset-index artifacts/multi_asset_report/multi_asset_report/multi_asset_research_index.json \
  --output-dir artifacts/scenario_stress
```

## Outputs

```text
scenario_stress_pack.json
scenario_stress_report.md
scenario_stress_results.json
scenario_stress_index.json
```

## Default scenarios

```text
base_observed
cost_slippage_pressure
data_scarcity_penalty
combined_research_stress
```

## Safety

This is descriptive research only.

It does not produce:

```text
allocation
portfolio weights
position sizing
signals
orders
recommendations
operational decisions
real-capital actions
```
