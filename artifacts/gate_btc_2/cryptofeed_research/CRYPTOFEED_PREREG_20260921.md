# Cryptofeed cross-venue microstructure standalone — preregistration

Date: 2026-09-21

## Purpose

Test whether Cryptofeed can provide a tangible, synchronized, cross-venue BTC spot order-book artifact and whether one frozen lead-lag hypothesis survives a short live sample.

This is external BTSE research only. It does not modify Factory logic, V2A, source registries, PIT collectors, runtime state, engine feeds, or capital allocation.

## External system

- Project: `bmoscon/cryptofeed`
- Release: `v2.5.0`
- Role under test: normalized multi-exchange L2 order-book capture
- Venues: Binance spot and OKX spot
- Symbol: `BTC-USDT`
- Channel: `L2_BOOK`
- Depth used: top of book only

## Frozen live-capture design

- capture duration: 120 seconds
- receipt clock: local monotonic/UTC receipt timestamp emitted by Cryptofeed callback context
- venues sampled simultaneously in one process
- no authenticated endpoints
- no orders
- no historical backfill
- no venue substitution after outcome

Each accepted update records:

- venue
- receipt timestamp
- best bid
- best ask
- midpoint
- quoted spread

Fail closed on crossed/empty/non-positive top of book.

## Frozen synchronization

- analysis grid: 250 ms
- last observation carried forward per venue only if age <= 2 seconds
- overlapping shared window only
- no interpolation across missing venue state

## Primary hypothesis

`H_CF_LL_01`:

> Binance BTC-USDT midpoint return in bucket `t` positively predicts OKX BTC-USDT midpoint return in bucket `t+1` at a 250 ms grid.

Primary statistic:

`corr(r_binance_t, r_okx_t+1)`

Control statistic:

`corr(r_okx_t, r_binance_t+1)`

No lag search is allowed after the result. The 250 ms lag is frozen before capture.

## Frozen minimum capture-quality gate

All must hold:

1. >= 100 valid top-of-book updates from Binance;
2. >= 100 valid top-of-book updates from OKX;
3. >= 60 seconds of shared valid overlap;
4. >= 200 synchronized 250 ms grid rows;
5. zero crossed books among accepted rows;
6. both venues have positive median quoted spread.

If this gate fails, disposition is `CAPTURE_NOT_ESTABLISHED` and the lead-lag hypothesis is not interpreted.

## Frozen lead-lag pass rule

`H_CF_LL_01` passes only if all hold:

1. primary correlation > 0.05;
2. primary correlation - reverse/control correlation > 0.02;
3. >= 100 return pairs with at least one non-zero leg.

Otherwise the frozen lead-lag hypothesis is rejected.

A pass is only a **candidate signal**, not an economic claim. No trading PnL claim is authorized by this 120-second standalone capture.

## Allowed dispositions

- `COMPONENT_PASS / LEAD_LAG_CANDIDATE`
- `COMPONENT_PASS / LEAD_LAG_REJECTED`
- `CAPTURE_NOT_ESTABLISHED`

## Integration boundary

No Factory integration occurs in this PR. If and only if the standalone capture-quality gate passes, a later BTSE integration test may compare the exact same frozen feature against an existing QRDS baseline in a separate preregistered experiment. A failed lead-lag hypothesis must not be retuned by lag shopping.

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
