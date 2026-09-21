# Coin Metrics on-chain standalone — preregistration

Date: 2026-09-21

## Purpose

Test whether one simple, frozen Bitcoin on-chain activity feature from the Coin Metrics Community API has tangible historical risk-filter value before considering any BTSE integration.

This is external BTSE research only. It does not modify Factory logic, V2A, PIT collectors, source registries, runtime state, engine feeds, orders, or capital.

## External system / source

- provider: Coin Metrics Community API v4
- authentication: none
- asset: `btc`
- frequency: `1d`
- metrics: `AdrActCnt`, `PriceUSD`
- requested historical window: `2020-01-01` through `2026-09-20`

The Community API is used as a historical research source only. This preregistration does **not** assume that today's historical response is a revision-versioned point-in-time dataset.

## Frozen hypothesis

`H_CM_ADDR_01`:

> A positive 7-day change in Bitcoin active addresses can act as a simple risk-on gate that materially reduces BTC drawdown without sacrificing more than 10% of final equity versus buy-and-hold.

No other on-chain metric, lookback, sign, threshold, z-score, smoothing rule, or combination may be tried after observing this result under this hypothesis.

## Frozen causal geometry

For metric day `t`:

- activity state = `LONG` iff `AdrActCnt_t > AdrActCnt_{t-7}`;
- otherwise state = `FLAT`;
- one full daily observation embargo is imposed;
- state computed from day `t` is applied only to the price return `PriceUSD_{t+1} -> PriceUSD_{t+2}`;
- no shorting;
- no leverage;
- missing/non-positive metric or price rows are not forward-filled.

This embargo is intentionally conservative and avoids using same-day on-chain data against the same day's price.

## Frozen economics

- initial equity: `10000`
- strategy: full notional BTC when LONG, cash when FLAT
- transaction cost: `10 bps` on each state transition side (entry or exit)
- baseline: buy-and-hold over the exact same valid target-return dates, with `10 bps` entry and `10 bps` final exit
- no slippage model beyond frozen costs

## Frozen primary pass rule

The risk gate passes only if both hold:

1. strategy maximum drawdown improves by at least `5 percentage points` versus baseline;
2. strategy final equity is at least `90%` of baseline final equity.

For clarity, if baseline max drawdown is `-50%`, condition 1 requires strategy max drawdown to be at least `-45%` or better.

## Frozen descriptive metrics

Report, but do not use for post-hoc pass redefinition:

- valid daily observations;
- fraction of days LONG;
- state transitions;
- strategy and baseline final equity / total return;
- strategy and baseline max drawdown;
- annualized return;
- annualized volatility;
- Sharpe-like return/volatility ratio using zero risk-free rate;
- delta in final equity and drawdown.

## Frozen minimum data gate

The result is interpretable only if all hold:

1. >= `1500` valid aligned source rows before feature construction;
2. >= `1400` valid causal target-return observations;
3. no duplicate timestamps;
4. timestamps strictly increasing after normalization;
5. both LONG and FLAT states occur;
6. >= `20` state transitions.

Failure produces `DATA_CAPABILITY_NOT_ESTABLISHED`.

## PIT / integration boundary

A historical pass may produce only:

`HISTORICAL_CANDIDATE / PROSPECTIVE_PIT_VALIDATION_REQUIRED`

because the Community API response retrieved today is not assumed to prove historical revision state as known on each original date.

A failed frozen hypothesis produces:

`FEATURE_REJECTED / SOURCE_RETAINED_AS_RESEARCH_COMPONENT`

No Factory integration is authorized from this historical run alone. Integrated BTSE use requires either:

- a provider-supported historical as-of/revision dataset; or
- fresh prospective accumulation under an immutable timestamped collection protocol.

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
