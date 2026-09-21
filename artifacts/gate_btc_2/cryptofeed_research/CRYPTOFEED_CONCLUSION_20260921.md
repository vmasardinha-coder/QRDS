# Cryptofeed cross-venue standalone conclusion — 2026-09-21

## Classification

`Cryptofeed = CONCLUDED / RETAIN_AS_CROSS_VENUE_MICROSTRUCTURE_COMPONENT`

Frozen signal hypothesis:

`H_CF_LL_01 = REJECTED`

No Factory migration is authorized by this result.

## Exact run

- PR: #886
- head SHA with successful standalone: `d31c0b01643363b952612d5bafeefea71c80c923`
- workflow run: `35660129278`
- artifact: `gate-btc-cryptofeed-crossvenue-standalone` / `10667540970`
- artifact digest: `sha256:18da4430512456034b5221ed8e536af08ba995012581b3d8b34b7bbec1d0b115`
- Cryptofeed: `2.5.0`
- venues: Binance Spot and OKX Spot
- symbol: `BTC-USDT`
- capture duration requested: 120 s
- actual wall duration: 125.50237512588501 s

## Mechanical repairs before scientific outcome

Two pre-outcome mechanical failures were repaired without changing the preregistered scientific question:

1. GitHub runner in a US region received HTTP 451 from `api.binance.com` before symbol resolution. Binance transport was moved to Binance's own public market-data mirror (`data-api.binance.vision` + `data-stream.binance.vision`), keeping the same Binance venue, symbol, channel, duration, feature, lag, and pass rules.
2. Cryptofeed enabled `uvloop`; Python 3.12 had no current event loop when the timer was armed. The runner now creates and registers the event loop explicitly. No scientific parameter changed.

## Tangible standalone artifact

Capture-quality gate: **PASS**.

- accepted normalized book events: `2119`
- Binance updates: `1188`
- OKX updates: `931`
- shared valid overlap: `118.5 s`
- synchronized 250 ms grid rows: `475`
- rejected events: `0`
- crossed books: `0`
- Binance median quoted spread: `0.010000000009313226`
- OKX median quoted spread: `0.09999999999126885`

Therefore Cryptofeed demonstrated the tangible capability that justified admission to the external radar: simultaneous normalized cross-venue top-of-book capture with a reproducible artifact.

## Frozen lead-lag result

Primary preregistered direction:

`corr(Binance return_t, OKX return_t+1) = 0.10875833307699101`

Reverse/control direction:

`corr(OKX return_t, Binance return_t+1) = 0.34808613791393067`

Primary minus control:

`-0.23932780483693966`

Effective primary pairs with at least one non-zero leg:

`27`

Frozen pass required all of:

1. primary correlation > 0.05;
2. primary - reverse > 0.02;
3. >= 100 non-zero primary pairs.

Only condition 1 passed. Conditions 2 and 3 failed.

Disposition:

`COMPONENT_PASS / LEAD_LAG_REJECTED`

## Scientific interpretation

The standalone establishes **data/capture capability**, not alpha.

The fact that the reverse/control correlation was numerically larger does not authorize flipping the hypothesis after observing the sample. Doing so would be direction shopping. The short sample also contained only 27 effective non-zero primary pairs, below the preregistered minimum.

A future OKX→Binance hypothesis would have to be a fresh preregistered experiment on an independent live sample, with its own effective-sample threshold and economic execution test. This run cannot be reused as proof for that direction.

## Integration decision

No integrated Factory test is justified for `H_CF_LL_01` because the standalone signal hypothesis failed.

Cryptofeed is retained externally for future genuinely new microstructure/cross-venue hypotheses because the capture component itself passed. It must not create parallel Factory runtime, V2A, PIT, registry, or source-management work.

## Safety outcome

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_BACKFILL=true`
- `NO_RETUNE=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`
