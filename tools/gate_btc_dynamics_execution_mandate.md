# Explicit Dynamics research execution mandate

This is a gate around the accepted spot/market simulator, not an active
Gateway strategy. It supports a frozen target admission, explicit UTC slots
and a documented minimum interval between mandated rebalances. Even a slot
with no fills is consumed. That interval is not an inferred per-asset hold.

The caller must resolve exact reviewed mandate bytes, SHA256 and publication
availability before the first allowed window. The source must already have
been published within the independent accounting protocol's epoch. A digest
does not by itself prove reviewer approval. No actual strategy policy is
created or approved by this module or its tests.

All fields are mandatory. An ordinary scanner recommendation such as weekly,
weekly_or_persistence or 2x_week_or_vol_trigger is not a calendar or signal.
The gate does not choose dates, thresholds, triggers or scientific rules.

Supported policy semantics must be explicit: literal non-interest-bearing
USDT with no FX/borrowing; source per-fill fee and slippage without charging
estimated daily drag again; a preauthorized exact target with no stop in
this independent mandate; calendar then minimum interval then rebalance.
Other stop, persistence, volatility, cash or precedence rules fail closed.
This does not disable or replace any existing strategy's stops.

`rebalance_mandated` enforces source/policy/protocol/cost bindings, ordered
nonoverlapping half-open UTC windows, target and market freshness, single
slot use, previous-receipt/state continuity and atomic market checks. A
different target or mandate cannot be spliced into a prior chain. A changed
strategy requires separate admission and an independent protocol/series.

No real mandate, seed capital, schedule, paper ledger or production collector
is installed. Fixture trades and deterministic tests are software evidence,
not observed market returns, scientific admission or deployment authority.
Production activation false; orders, real capital and scientific credit zero.
