# Safety Policy — crypto_decision_lab

## Mode

```
INTERACTIVE_RESEARCH_ONLY
```

This system is a quantitative research tool. It has no operational mode.

## Hard constraints — never violated

| Flag | Required value |
|---|---|
| `api_key_present` | `False` |
| `api_key_required` | `False` |
| `account_connection_required` | `False` |
| `authenticated_connection_used` | `False` |
| `orders_generated` | `False` |
| `real_orders_generated` | `False` |
| `real_capital_used` | `False` |
| `operational_decision_allowed` | `False` |

## What is allowed

- Simulation and fixture replay (Binance)
- Public HTTP live market data without authentication (OKX)
- Offline feature engineering, regime diagnostics, target labels
- Research-only backtest and risk engine
- Offline paper trading simulation
- Interactive research dashboard (HTML and Streamlit)
- JSON/TXT export of research artifacts

## What is NOT allowed

- Any exchange API key or secret
- Any authenticated HTTP or WebSocket connection
- Any real order placement (buy/sell)
- Any real capital deployment
- Any leverage
- Binance used as a real execution base
- Automated operational decisions

## Enforcement

Safety gates are enforced in code via `safety/gates.py`. Every pipeline calls
`assert_research_only()` before returning results. Tests in `tests/safety/`
verify these gates at every CI run.
