# QRDS/QOS Data Coverage Gate v1

The Data Coverage Gate is a research-only review layer for upstream data and evidence artifacts.

It answers whether coverage appears sufficient for continued research diagnostics. It does **not** authorize trading, allocation, orders, recommendations, signals, position sizing, authenticated exchange access, API keys, or real-capital use.

## Contract

- App mode: `INTERACTIVE_RESEARCH_ONLY`
- Explicit report paths only inside the Python builder
- From-stack discovery only in the shell wrapper
- Policy lock remains active
- No operational use is unlocked

## Commands

Isolated mode:

```bash
cd /workspaces/QRDS
bash qrds_data_coverage_serve.sh --output-dir artifacts/data_coverage --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Stack mode:

```bash
cd /workspaces/QRDS
bash qrds_data_coverage_from_stack_serve.sh
```
