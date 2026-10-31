# Dynamics: isolated spot accounting kernel

This pure Python module implements only the spot portion of the DYN05
accounting dependency inside permanent queue item C1. It is disconnected from
collectors, strategy selection, brokers, daily production NAV and activation.
No existing Gateway profile is enabled by this module.

Every protocol explicitly binds currency, activation boundary, initial cash,
instrument identity/venue/market, lot size, fee and slippage per side, and a
price-age bound. The kernel checks completeness; it cannot certify that a
supplied identity/hash is true or prove that a quote is the first available
quote after publication. Those require independently verified source binding.

Genesis contains cash only. A fill requires a prospective signal publication
and a later quote, provenance hashes, chronology, cash and whole lots. Fills
are immutable state transitions; a failed fill cannot mutate cash or history.
Fees apply to actual traded notional. Modeled slippage changes the fill price
and is reported separately without being deducted a second time. NAV is cash
plus marked spot quantities. Every held asset requires a recent, nonfuture
mark at or after the latest accounting event; missing marks fail closed.
Receipts link the frozen protocol and previous event hash.

Only same-currency, unlevered spot inventory is supported. Derivatives,
borrowed shorts, funding, FX, margin and liquidation are explicitly unsupported.
No fee or slippage rate is silently selected. Tests use obvious synthetic
prices/costs and TEST_VENUE identities; their NAVs are not economic evidence.

The caller remains responsible for causal signal input, verified execution
sources and deterministic event generation. Cadence, hold, persistence,
stops, event precedence, quote availability and activation governance remain
unbound for the eight Gateway profiles. A past timestamp accepted during
offline replay does not authorize retroactive production history. There is
no checkpoint loader, live entrypoint or automatic production schedule.

Validation uses independent hand calculations for round trips, turnover costs
and multi-asset inventory, plus rejection of lookahead, stale/missing marks,
protocol drift, duplicates, shorts and unfunded transactions.
