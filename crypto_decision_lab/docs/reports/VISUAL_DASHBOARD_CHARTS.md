# QRDS Visual Dashboard Charts v1

Sprint 8H adds visual chart panels to the dashboard.

## Command from repository root

```bash
bash qrds_dashboard_charts.sh \
  --output-dir artifacts/dashboard_charts \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Open:

```text
artifacts/dashboard_charts/charts/index.html
```

## Panels

```text
edge score bars by asset
worst stress score bars by asset
mean scenario stress bars
scenario table
safety locks
```

## Safety

This is a visual research viewer.

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
