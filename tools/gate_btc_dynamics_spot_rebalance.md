# Dynamics —atomic spot rebalance primitive

The previous kernel accepted individual paper fills. This primitive accepts an explicit target allocation and produces the complete sell/buy batch, actual modeled turnover/costs, lot residuals and a hash-bound seal. If any step fails, the caller's immutable starting state remains unchanged and no partial batch is returned.

Inputs must explicitly bind the strategy protocol, activation, exact same-currency spot instruments, lot sizes, per-side fees/slippage, a published signal hash/time, a rebalance ID, CASH weight and valid quotes strictly after the signal. Nonnegative weights must sum exactly to1; a profile label never chooses these values. Shorts, leverage, FX, funding and derivatives are rejected by the original kernel.

Sizing policy:

1. Calculate reference NAV from cash, existing quantities and validated input quotes.
2. Round desired target quantities down to their explicit lots.
3. Sell excess quantities first.
4. Reserve the explicit CASH target calculated from pre-trade reference NAV.
5. Scale all requested purchases proportionally if their fee/slippage-inclusive cost exceeds available cash; floor every purchase to its lot.
6. Execute purchases in stable asset order and retain unused cash. Report achieved weights and residual cash.
7. Reconcile reference NAV reduction against modeled fees and adverse slippage, then seal the complete batch. A no-trade batch still seals its ID and clock without fictitious turnover.

Quotes reused for this reconciliation are not fresh post-execution marks. The result explicitly sets economic_result_available=false and fresh_post_execution_nav_available=false. A later economic valuation still calls the unchanged kernel with fresh, complete marks after the last accounting event.

Independent examples covered by tests include equal two-asset allocation, cash raised by selling before purchasing, proportional fee budgeting, coarse-lot residual cash, unchanged holdings with zero turnover, and cash/inventory reconciliation with slippage counted once. A collision in the final buy rejects the complete batch even after local simulation of a sale.

Integration status: accounting infrastructure only. This does not turn historical Gateway composition snapshots into economic observations, activate any of its8 profiles, freeze unspecified rebalance/hold/stop rules, bind a trading venue, or generate orders. Source code describes3 profiles without negative weights and5 involving shorts; nonnegative weights alone do not certify instrument type or make a profile executable.
