# QRDS Interactive Static Dashboard UX

Sprint 8F adds client-side usability controls to the static dashboard.

## Command from repository root

```bash
bash qrds_dashboard_ui.sh \
  --output-dir artifacts/dashboard_ui \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Open:

```text
artifacts/dashboard_ui/interactive/index.html
```

## Controls

```text
symbol search
edge status filter
worst stress status filter
sort by symbol
sort by edge score
sort by worst stress score
```

## Safety

This remains a local static dashboard.

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
