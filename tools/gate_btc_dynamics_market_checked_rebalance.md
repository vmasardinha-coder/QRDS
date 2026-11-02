# Dynamics research rebalance with MARKET constraint checks

The existing accounting/rebalance primitives remain unchanged. The new pure
wrapper binds the admitted profile, exact protocol instruments and sealed market
audit, simulates all fills privately, and returns a newly sealed state only if
every modeled order passes LOT_SIZE, MARKET_LOT_SIZE and applicable notional
limits. A late purchase failure cannot commit earlier simulated sales. Invalid
orders are not clipped, split, skipped, substituted or reweighted.

The wrapper requires an explicit execution-time metadata-age bound no looser
than the audit bound. A market audit created after execution, missing held-asset
metadata, changed admission, different venue/identity/currency or protocol lot
blocks the operation. A removed holding still needs audited market coverage;
missing metadata is not permission to liquidate it using an inferred pair.

Notional checks use their own hash-bound reference, not a fill's modeled price.
An observed exchange reference takes precedence. Otherwise a caller must supply
evidence of a null exchange reference and the VWAP matching avgPriceMins, or the
last price when that window is zero. Every reference has exact market/currency,
availability clock and provenance. Missing, stale, future or incorrectly bound
references abort the operation. Applicability flags control minimum/maximum
checks. Quantity steps of zero in MARKET_LOT_SIZE do not trigger division by zero.

Specification: Binance official spot filter documentation,
https://developers.binance.com/en/docs/products/spot/filters .

This is an explicitly limited research check, not proof an exchange would accept
an order. MARKET orders carry no limit/stop price; account counters, permissions,
other exchange/asset-wide restrictions and broker matching are not verified.
Known out-of-scope filters remain visible in the receipt; unknown filter types
block this wrapper. All receipts say exchange_order_eligibility_proven=false.

There are no network calls, schedules, broker credentials, production activation,
real orders, economic observation credit or retrospective NAV. Calendar, hold,
stop, precedence, cash/quote treatment and modeled cost choices remain explicit
protocol requirements. A fresh post-fill economic mark is still required by the
accounting kernel. Synthetic regression fixtures are not production returns.

Run the complete offline suite:

```sh
python -m unittest discover -s tests -p 'test_gate_btc_dynamics_*.py' -v
```
