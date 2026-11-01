# V16 research shadow —independent series

Requested on31October2026: retain the V16B1 prospective corpus and add a parallel economic monitor comparable in presentation to V13.

This series reuses V16's18 features and classifier parameters. It trains on730 completed days of Binance Spot history for the exact identities in a hash-bound current CMC Top150 capture. Reusing current membership historically has survivorship bias: it is explicitly labeled FIXED_CURRENT_UNIVERSE_HISTORICAL_SEED_BIASED. It is not historical point-in-time membership, a recovered V16 historical replay or evidence credited to V16B1. At least52 qualified, fully matured training weeks are required. Future feature rows and matured labels are retained independently and immutably.

The original V16B1 keeps its own52-prospective-week training requirement, corpus, contracts and counters. The publishing workflow compares hashes of all V16B1 ledger/evidence files before and after the independent run.

The new series uses Thursday UTC closed features, a Friday entry plan sealed before that day's UTC close, and a modeled fill at the completed Friday close. It holds for one week; daily marks compare its own normalized NAV against BTC over the same anchor. A missed entry plan is skipped, never backdated. Missing intermediate daily marks are explicit multi-day intervals and do not manufacture daily observation counts. The first eligible signal is the first Thursday strictly after activation:5November if activation completes31October; planned entry6November and first weekly exit13November.

Longs are10 exact Binance Spot USDT instruments; shorts are the first10 exact live OKX USDT swaps in the frozen ascending ranking. Each side has50% unscaled gross exposure. Model ties use symbol ascending. The13-cycle risk history starts empty, uses this series only and targets20% annualized volatility with maximum exposure1. Retraining occurs every13 scoring weeks.

Fees/slippage are modeled together at15bps of net traded notional; unchanged holdings do not incur a fictitious full round trip. Paper quantities are self-financed after modeled costs. Funding rates are official observations; cash impact is modeled using base quantity and the official1-minute opening mark at settlement. This is not observed account cash flow. There is no exchange authentication, order execution, real capital, margin sufficiency claim or promotion authority.

Own outputs:STATUS.json, EVENTS.jsonl, ECONOMICS.csv and REPORT.html under runtime/ledgers/v16_research_shadow_20261031. Before the first entry, NAV is null and economic observations are zero. Historical training readiness is never presented as a positive investment return.

The daily workflow runs at01:15UTC (22:15BRT on the previous calendar day); the Friday entry-plan check runs at21:10UTC (18:10BRT). It can also be dispatched manually. Raw source responses and their hashes are retained inside the independent ledger and its workflow artifact. Main source owns this implementation; no ChatGPT reminder is required to run the GitHub workflow.
