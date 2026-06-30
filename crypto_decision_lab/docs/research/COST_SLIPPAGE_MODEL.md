# Cost & Slippage Research Model

Sprint 7E adds a simple research-only cost model.

It applies conservative bps assumptions to hypothetical backtest replay events.

## Model

```text
turnover = abs(current_exposure - previous_exposure)
fee_cost = turnover * fee_bps / 10_000
slippage_cost = turnover * slippage_bps / 10_000
borrow_cost = abs(current_exposure) * borrow_bps / 10_000
net_return = gross_hypothetical_return - total_cost
```

## Important limitation

This is not execution modeling.

It does not model:
- order book depth
- real fills
- market impact curves
- exchange-specific fees
- funding
- latency
- liquidation
- live routing

## Safety

The module is offline and research-only.

It does not produce:
- orders
- executable signals
- recommendations
- operational decisions
- real-capital outputs
