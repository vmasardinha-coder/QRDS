# QRDS Smart Dashboard Server Port UX

Sprint 8G adds smart port selection for the dashboard.

## Generate plan

```bash
bash qrds_dashboard_serve.sh \
  --output-dir artifacts/dashboard_ui \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

It prints:

```text
SMART DASHBOARD READY
SELECTED PORT
SERVE COMMAND
CODESPACES PORT HINT
```

## Serve with auto-selected port

```bash
bash qrds_dashboard_serve.sh \
  --output-dir artifacts/dashboard_ui \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT \
  --serve
```

If port 8000 is busy, it automatically tries 8001, 8002, etc.

To stop the server:

```text
Ctrl+C
```

## Safety

This is only a local static dashboard server.

It does not produce allocation, signals, orders, recommendations, operational
decisions or real-capital actions.
