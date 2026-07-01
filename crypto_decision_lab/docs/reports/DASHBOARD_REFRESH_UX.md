# QRDS Dashboard Refresh & Locator UX

Sprint 8D adds a single refresh command that generates the dashboard and prints
where to open it.

## Command from repository root

```bash
bash qrds_dashboard_refresh.sh
```

Optional explicit command:

```bash
bash qrds_dashboard_refresh.sh \
  --output-dir artifacts/dashboard \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

## Outputs

```text
artifacts/dashboard/dashboard/index.html
artifacts/dashboard/dashboard_launch_info.json
artifacts/dashboard/OPEN_DASHBOARD.md
```

## User action

Open:

```text
artifacts/dashboard/dashboard/index.html
```

or right-click `index.html` and choose `Open Preview`.

## Safety

This remains static, offline and research-only.

It does not produce allocation, signals, orders, recommendations, operational
decisions or real-capital actions.
