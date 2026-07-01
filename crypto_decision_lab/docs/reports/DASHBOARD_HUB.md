# QRDS Dashboard Hub v1

Sprint 8I adds a local dashboard hub.

## Command from repository root

```bash
bash qrds_dashboard_hub.sh \
  --output-dir artifacts/dashboard_hub \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Open:

```text
artifacts/dashboard_hub/hub/index.html
```

## What it links

```text
interactive dashboard
visual charts dashboard
machine-readable payload files
safety locks
```

## Safety

This is a local static hub.

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
