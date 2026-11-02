# Dynamics spot market metadata audit

`audit_markets` checks explicit Binance spot candidates declared by the scanner
against a captured, official public `/api/v3/exchangeInfo` response. It is pure
and performs no network calls, orders, portfolio activation or ledger writes.

Inputs are an unchanged target admission, explicit asset-to-market candidates,
exact scanner CSV bytes and SHA256, exact metadata bytes, allowed source URL,
capture/admission clocks, explicit metadata age bound and quote currency.
The metadata capture must follow availability of the targets and cannot be
future or stale under the caller's stated audit bound.

Each binding must occur exactly once in the hashed scanner, be marked spot
available, and match the exchange symbol, base and quote exactly. No market is
inferred from a ticker. Missing, halted, mismatched or incomplete markets remain
explicit gaps in each affected profile. No target is removed or renormalized.
The three spot profiles are covered; the five derivative profiles are excluded.

The audit preserves price, quantity and notional filters, including distinct
`LOT_SIZE` / `MARKET_LOT_SIZE`, zero market step, market applicability flags and
`avgPriceMins`. Missing, duplicated, nonfinite or invalid required filters block
coverage. Other filters are retained, not declared implemented by the executor.

Complete metadata means only that public market specifications were captured.
It does not establish account permissions, blockchain identity, venue approval,
cash/USDT/USD equivalence, executable prices, fees, slippage or strategy rules.
The existing spot executor is not automatically connected to these candidates:
filter enforcement requires its own reference prices and windows. Every output
keeps `executable=false`, identity/account approval false, zero economic credit,
zero orders and no production activation. Audits bind the exact source bytes
with hashes, so later changes require a new receipt.

Run offline checks with:

```sh
python -m unittest discover -s tests -p 'test_gate_btc_dynamics_*.py' -v
```
