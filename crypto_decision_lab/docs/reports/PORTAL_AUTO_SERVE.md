# QRDS Portal Auto Serve

8K hotfix adds explicit server startup for the unified portal.

## Generate and start server

```bash
bash qrds_dashboard_portal.sh \
  --output-dir artifacts/dashboard_portal \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT \
  --serve
```

or:

```bash
bash qrds_portal_serve.sh \
  --output-dir artifacts/dashboard_portal \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

The server keeps running until:

```text
Ctrl+C
```

## Codespaces

Open:

```text
Ports → selected port → Open in Browser / Open Preview
```

If the popup does not appear, use the Ports tab manually.

## Safety

Static local research portal only. No signals, allocation, recommendation,
orders, real capital or account access.
