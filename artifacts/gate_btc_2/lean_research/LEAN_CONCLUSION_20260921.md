# QuantConnect LEAN — Scientific Conclusion — 2026-09-21

## Scope
- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- Factory untouched.
- Upstream LEAN SHA: `985ef30ad3ac774218c5ac516b4cb0aa2655730f`.

LEAN was evaluated primarily as an industrial backtest/execution realism source rather than as an alpha generator.

## Tested component: VolumeShareSlippageModel

LEAN formula:

`volume_share = min(order_quantity / bar_volume, volume_limit)`

`slippage_pct = volume_share^2 * price_impact`

Frozen defaults from LEAN:
- `volume_limit = 0.025`
- `price_impact = 0.10`

Audit data:
- OKX BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT
- 1h, 4,000 bars per asset
- 10% NAV hypothetical order size
- NAV stress: $10k, $100k, $1m, $10m

## Key results

The default LEAN parameters mechanically cap slippage at:

`0.025^2 * 0.10 = 0.0000625 = 0.625 bps`

### Mean slippage / saturation rate

| Asset | $10k NAV | $100k NAV | $1m NAV | $10m NAV |
|---|---:|---:|---:|---:|
| BTC | 0.000025 bps / 0.0% | 0.00249 / 0.0% | 0.15476 / 8.88% | 0.59074 / 89.33% |
| ETH | 0.000091 / 0.0% | 0.00907 / 0.03% | 0.29659 / 27.03% | 0.61347 / 96.48% |
| SOL | 0.000762 / 0.0% | 0.07036 / 1.40% | 0.56570 / 80.83% | 0.62490 / 99.95% |
| XRP | 0.003170 / 0.0% | 0.20439 / 12.98% | 0.60464 / 93.88% | 0.62491 / 99.98% |

At the small/mid capital levels relevant to many QRDS experiments, the default model adds negligible cost for BTC/ETH and modest stress for lower-liquidity assets. At larger order sizes, the model rapidly reaches its mechanical ceiling rather than continuing to increase impact.

## Interpretation

This makes the model useful as a **capacity flag / relative liquidity diagnostic**, but not sufficient as the final execution-cost model for large orders. Once the volume-share cap is reached, economic impact is no longer increasing with order size even though real-world market impact generally can.

The result also means blindly importing LEAN defaults would risk a false sense of execution realism for large positions.

## Decision

`VolumeShareSlippageModel = KEEP_RESEARCH_CAPACITY_DIAGNOSTIC`

`LEAN = CONCLUDED / RETAIN_AS_EXECUTION_AND_BACKTEST_AUDITOR`

Do not treat LEAN as an alpha source based on this work. Do not migrate the default slippage parameters into the Factory as canonical execution economics. If used later, they should be one stress scenario among multiple impact models, ideally alongside order-book/depth replay and venue-specific costs.

## Runtime evidence
- workflow run: `35606539881`
- job: `106354896878`
- artifact ID: `10642765334`
- artifact SHA256: `ff18dee757076f94ed77c4184104d9c120b06d6f8f2dbbd9bc4e3c4f7c22621d`

No Factory migration was performed.
