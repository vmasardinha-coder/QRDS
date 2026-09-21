# QuantLib + Deribit BTC options standalone conclusion — 2026-09-21

## Classification

`QuantLib = CONCLUDED / RETAIN_AS_OPTIONS_PRICING_AUDITOR`

Standalone capability: **PASS**.

No alpha, economic benefit, or Factory migration is authorized by this result.

## Exact scientific run

- PR: #887
- successful preregistered head: `a06d606e8d4f3b4fdf4713573d0a992a95033411`
- workflow run: `35661470609`
- artifact: `gate-btc-quantlib-deribit-options-standalone` / `10666732589`
- artifact digest: `sha256:c196698c08925dbb14e758cc972eeba994619b048d7acda15ce3b87896bd18f7`
- QuantLib: `1.43`
- Deribit currency: BTC
- Deribit kind: option
- live BTC index: `86580.77`

Raw evidence SHA-256:

- index: `6e385f410412d9cde43bc8041c4e2e319cda54b3a7bf78fd731b4e5830804ff0`
- instruments: `6b8dc472df31e633c8de007ef0d7ae7feb1516b006defc6816a8b1b4aa79abed`
- book summaries: `0168608d24070e87bbc69727426534385bf8df61140164b02e36e72b1da2368d`

## Tangible chain artifact

Raw Deribit corpus:

- instruments: `984`
- book summaries: `984`

Accepted by the preregistered model-input rules:

- total options: `957`
- calls: `477`
- puts: `480`
- distinct expiries: `11`
- duplicate accepted names: `0`
- all reconstructed values finite/non-negative: `true`
- rejected for non-positive model inputs: `27`

The frozen minimum-sample gate therefore passed by a wide margin.

## Frozen QuantLib reconstruction result

Using Deribit's documented inverse-option geometry — live BTC index `X`, expiry forward `F`, `r = ln(F/X)/T`, Deribit mark IV, exact strike/type/expiry — QuantLib `BlackCalculator` reconstructed the BTC mark prices with:

- median absolute error: `0.0000021162753135184342 BTC`
- 90th-percentile absolute error: `0.00001536526186751985 BTC`
- median absolute relative error for marks >= 0.002 BTC: `0.00007464976716329891` (~`0.00746%`)
- relative-error eligible sample: `802`
- fraction with absolute error <= 0.002 BTC: `1.0` (`100%`)

Frozen pass rules were:

1. median absolute error <= `0.0005 BTC`;
2. p90 absolute error <= `0.0020 BTC`;
3. median absolute relative error <= `2.5%` for marks >= `0.002 BTC`;
4. >= `90%` of accepted instruments within `0.0020 BTC`.

All four passed with substantial margin.

Disposition:

`CONCLUDED / RETAIN_AS_OPTIONS_PRICING_AUDITOR`

## What is tangible

This experiment establishes a capability that was absent from the QRDS/BTSE inventory before this run:

- public live BTC option-chain ingestion;
- exact instrument/expiry/strike/type normalization;
- independent QuantLib pricing from venue-published IV/forward inputs;
- reproducible chain-level mark consistency audit;
- per-expiry IV-range and reconstruction-error summaries;
- raw evidence hashes for later audit.

The artifact is useful as an external derivatives-pricing/volatility-surface auditor.

## What this does NOT establish

This result does not show:

- predictive alpha;
- profitable options trading;
- an options-derived signal improving QRDS;
- a volatility risk premium edge;
- a skew/carry strategy;
- incremental economic gain over the Factory;
- permission to create a parallel Factory options runtime.

The test used Deribit's own published mark IV as a model input and checked independent pricing consistency. Therefore the correct claim is **pricing/audit capability**, not discovery of mispricing.

## Integration decision

No Factory integration in this PR.

A later integrated experiment is justified only when there is a separately preregistered options-derived hypothesis with a frozen QRDS comparator. Generic funding/basis is excluded because that lane is already owned by the Factory.

Promising future hypotheses, if independently preregistered, include skew/term-structure state as a risk/context feature or options-implied distribution information. They must be tested standalone first on fresh evidence and then against an existing QRDS baseline; this conclusion does not grant them credit.

## Safety outcome

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`
