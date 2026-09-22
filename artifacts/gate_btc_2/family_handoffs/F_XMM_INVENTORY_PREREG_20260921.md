# F-XMM-INVENTORY — preregistered family handoff

Date: 2026-09-21

## Purpose

Extract a reusable **order-book pressure / inventory-state family** from the validated Cryptofeed live L2 capability and the Hummingbot inventory-skew research idea, without integrating either external platform.

This is explicitly distinct from the rejected `H_CF_LL_01` Binance->OKX 250 ms lead-lag hypothesis. No lead/lag direction, return target or venue winner is imported.

## Family identity

- family_id: `F-XMM-INVENTORY`
- class: `MICROSTRUCTURE / ORDER_BOOK_PRESSURE`
- origins: `Cryptofeed`, `Hummingbot`
- source market: BTC-USDT spot L2
- venues for capability validation: Binance Spot public mirror and OKX Spot
- research boundary: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `REAL_CAPITAL_BRL=0`, `ORDERS=0`

## Frozen per-book feature geometry

For ordered bid/ask levels `(price_i, size_i)` with `i=1` best:

1. `spread_bps = (ask1 - bid1) / mid * 10000`
2. `imbalance_l1 = (bid_size_1 - ask_size_1) / (bid_size_1 + ask_size_1)`
3. `imbalance_l5 = (sum_bid_size_1_5 - sum_ask_size_1_5) / total_size_1_5`
4. `imbalance_l10 = (sum_bid_size_1_10 - sum_ask_size_1_10) / total_size_1_10`
5. `microprice_deviation_bps`
   - `microprice = (ask1 * bid_size_1 + bid1 * ask_size_1) / (bid_size_1 + ask_size_1)`
   - `(microprice - mid) / mid * 10000`
6. `bid_concentration_l1_l10 = bid_size_1 / sum_bid_size_1_10`
7. `ask_concentration_l1_l10 = ask_size_1 / sum_ask_size_1_10`
8. `imbalance_shape = imbalance_l1 - imbalance_l10`

No return direction rule is frozen here.

## Snapshot eligibility

A book snapshot is eligible only if:

- at least 10 valid bid levels and 10 valid ask levels are present;
- bids are strictly descending by price;
- asks are strictly ascending by price;
- best bid <= best ask;
- all prices and sizes are finite positive;
- all eight features are finite;
- all imbalance features remain in [-1, 1].

Invalid snapshots are rejected, never neutralized.

## Capture validation gate

The standalone family extractor must establish the ability to produce the frozen features from live books, not alpha. For a 60-second capture:

- >=100 eligible snapshots per venue;
- >=30 seconds shared venue overlap;
- zero crossed accepted books;
- positive median spread on each venue;
- >=95% of received callbacks either accepted or explicitly rejected with a reason.

## Factory child-hypothesis axes allowed later

Only after an admissible timestamped feature panel exists, the Factory may generate/test child hypotheses from the frozen geometry, including:

- persistent positive/negative depth imbalance;
- microprice displacement relative to mid;
- shallow-vs-deep imbalance disagreement via `imbalance_shape`;
- liquidity concentration / fragility states;
- cross-venue consensus or disagreement at the same observation time;
- use as an entry gate, abstention layer, sizing/risk state, or independent family.

Any horizon, aggregation window, sign, threshold, venue-combination rule or execution mapping must be preregistered/generated under normal Factory discipline. None is supplied by this handoff.

## Explicit prohibitions

- Do not revive `H_CF_LL_01` or flip its direction post hoc.
- Do not treat live feature values as historical PIT evidence.
- Do not infer alpha from the ability to capture L2 data.
- Do not import Hummingbot inventory-skew parameters or external PnL.
- No Factory runtime, registry, order, capital or engine mutation.

## Disposition

`F-XMM-INVENTORY = FAMILY_SPEC_READY / LIVE_DEPTH10_VALIDATION_REQUIRED / ECONOMIC_CLAIM_NOT_AUTHORIZED`
