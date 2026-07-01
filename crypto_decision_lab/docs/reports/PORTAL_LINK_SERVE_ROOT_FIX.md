# QRDS Portal Link + Serve Root Fix

8K hotfix 2 changes the unified portal layout so the portal root is served,
not only the nested `portal/` folder.

## Why

The old portal could generate links like:

```text
../guide_page/guide/index.html
```

When the server was started inside the nested `portal/` directory, sibling
folders were outside the server root and could fail when clicked.

## New layout

```text
artifacts/dashboard_portal/index.html
artifacts/dashboard_portal/guide_page/guide/index.html
artifacts/dashboard_portal/interactive_page/interactive/index.html
artifacts/dashboard_portal/visual_page/charts/index.html
artifacts/dashboard_portal/dashboard_serve_plan.json
```

## Generate and start server

```bash
bash qrds_portal_serve.sh \
  --output-dir artifacts/dashboard_portal \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

The terminal remains running. Stop it with:

```text
Ctrl+C
```

## Codespaces

Open:

```text
Ports → selected port → Open in Browser / Open Preview
```

## Safety

Static local research portal only. No signals, allocation, recommendation,
orders, real capital or account access.
