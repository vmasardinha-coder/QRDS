# Dynamics source cost assumptions

The frozen Gateway producer declares 6 bps fee and 8 bps slippage per side.
Its daily trading drag is assumed turnover × (fee + slippage) × 2. The daily
profile number must never become a per-fill fee or be charged again on top
of modeled fill costs. These are source model assumptions, not observed
account fees or a confirmed commission tier.

`audit_costs` consumes the exact source ZIP, an explicit expected ZIP SHA256,
the admitted execution-profile CSV and its existing target admission. It
checks the immutable inputs, parses top-level literal constants without
executing producer code, and reconciles the three spot profile estimates.
The receipt retains both hashes and the original rebalance labels.

`bind_cost_assumptions` returns new immutable candidate instrument bindings
with those separate rates. Only exact Binance Spot USDT instruments are
accepted. It does not create a SpotProtocol, seed a ledger or assume USD
equals USDT. No schedule, persistence threshold, hold/stop/precedence rule,
cash yield, account permission or exchange approval is inferred.

The archive digest must be resolved against the canonical pinned producer
before calling the audit. A caller-supplied digest alone is not a scientific
admission. Fixtures test software; acceptance against the frozen source and
real admitted profile bytes is a separate receipt.

Research-only; no activation, orders, capital or economic observations.
