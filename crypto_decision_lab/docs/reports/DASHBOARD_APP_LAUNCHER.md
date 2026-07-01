# QRDS Local Dashboard App Launcher

Sprint 8E adds an app-style launcher for the static dashboard.

## Refresh and locate

From repository root:

```bash
bash qrds_dashboard_app.sh
```

This writes:

```text
artifacts/dashboard/dashboard/index.html
artifacts/dashboard/dashboard_app_launch.json
artifacts/dashboard/APP_READY.md
```

## Optional static server

```bash
bash qrds_dashboard_app.sh --serve
```

Then open:

```text
Codespaces → Ports → 8000 → Open in Browser / Open Preview
```

## Safety

The launcher is only a local viewer.

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
