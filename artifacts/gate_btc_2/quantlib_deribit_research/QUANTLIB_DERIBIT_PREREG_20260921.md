# QuantLib + Deribit BTC options standalone — preregistration

Date: 2026-09-21

## Purpose

Test whether QuantLib can independently reproduce the live Deribit BTC inverse-option mark prices from Deribit's published mark IV / forward inputs and produce a tangible option-chain audit artifact.

This is external BTSE research only. It does not modify Factory logic, funding/basis lanes, V2A, PIT collectors, source registries, runtime state, engine feeds, orders, or capital.

## External system

- Analytics library: QuantLib Python `1.43`
- Market venue/data source: Deribit public API
- Currency: BTC
- Instrument kind: option
- Contract family: inverse BTC options
- Authentication: none

Deribit documents inverse options as European-style, cash-settled contracts priced in BTC. The displayed IV uses the forward rather than the spot/index as the underlying input. The documented interest-rate relation is `r = ln(F/X)/T`, where `F` is the expiry forward and `X` the BTC index.

## Frozen live-data inputs

The run must capture and hash raw responses for:

1. `public/get_index_price?index_name=btc_usd`
2. `public/get_instruments?currency=BTC&kind=option&expired=false`
3. `public/get_book_summary_by_currency?currency=BTC&kind=option`

The runner must join by exact `instrument_name` and retain only instruments that have:

- option metadata with strike, expiry and call/put type;
- positive `mark_price`;
- positive `mark_iv`;
- positive `underlying_price` / expiry forward;
- expiry strictly after observation time;
- BTC inverse option naming/metadata consistent with the instrument record.

No strike, expiry or liquidity search may be performed after observing reconstruction errors.

## Frozen QuantLib reconstruction

For each accepted instrument:

- `X` = live `btc_usd` index;
- `F` = Deribit `underlying_price` from book summary;
- `K` = instrument strike;
- `T` = exact seconds from capture timestamp to expiry divided by `365 * 24 * 3600`;
- `sigma` = `mark_iv / 100`;
- `r = ln(F/X)/T`;
- discount factor `D = exp(-r*T) = X/F`;
- option type = call or put from instrument metadata;
- QuantLib engine = `BlackCalculator` with forward `F`, standard deviation `sigma*sqrt(T)`, discount `D`;
- reconstructed USD premium = QuantLib value;
- reconstructed BTC premium = USD premium / `X`.

Comparison target:

- Deribit `mark_price` in BTC.

This is deliberately a mark-consistency/capability audit, not a trading or alpha test.

## Frozen minimum sample gate

The result is interpretable only if:

1. >= 30 accepted BTC options total;
2. >= 10 accepted calls;
3. >= 10 accepted puts;
4. >= 2 distinct expiries;
5. zero duplicate accepted instrument names;
6. all reconstructed prices are finite and non-negative.

If this gate fails, disposition is `CAPTURE_OR_SAMPLE_NOT_ESTABLISHED`.

## Frozen capability pass rule

QuantLib reconstruction passes only if all hold across the accepted sample:

1. median absolute mark-price error <= `0.0005 BTC`;
2. 90th-percentile absolute mark-price error <= `0.0020 BTC`;
3. median absolute relative error <= `2.5%` for instruments with Deribit mark_price >= `0.002 BTC`;
4. >= `90%` of accepted instruments have absolute mark-price error <= `0.0020 BTC`.

No threshold, formula, interest convention, expiry selection, strike selection or option subset may be changed after observing the live result, except a demonstrably mechanical public-API/schema correction that leaves the scientific question unchanged.

## Secondary descriptive artifact

For auditability only, the output will also summarize by expiry:

- number of calls / puts;
- strike range;
- mark-IV range and median;
- reconstruction-error distribution.

These summaries do not create additional pass/fail criteria and do not authorize surface trading signals.

## Allowed dispositions

- `CONCLUDED / RETAIN_AS_OPTIONS_PRICING_AUDITOR`
- `CONCLUDED / QUANTLIB_MARK_RECONSTRUCTION_FAILED`
- `CAPTURE_OR_SAMPLE_NOT_ESTABLISHED`

A pass establishes a tangible external capability: independent derivatives-pricing/IV-surface audit. It does **not** establish alpha, economic benefit, or Factory migration.

## Integration boundary

No Factory integration occurs in this PR. A later integrated experiment is justified only if a separately preregistered QRDS hypothesis needs options-derived information and has a frozen baseline/comparator. Generic funding/basis work is explicitly out of scope because the Factory already owns that lane.

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`
