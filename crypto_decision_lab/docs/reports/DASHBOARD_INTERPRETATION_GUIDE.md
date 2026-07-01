# QRDS Dashboard Interpretation Guide v1

Sprint 8J adds a user-facing interpretation guide for the dashboard.

## Command from repository root

```bash
bash qrds_dashboard_guide.sh \
  --output-dir artifacts/dashboard_guide
```

Open:

```text
artifacts/dashboard_guide/guide/index.html
```

## What it explains

```text
edge status
edge score
worst stress
rows
splits
filters
safe questions
unsafe questions
current phase limits
```

## Safety

This is a reading guide only.

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
