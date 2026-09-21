# BOCPD structural-break risk overlay — conclusion

Date: 2026-09-21

## Classification

`CONCLUDED / REJECT_FROZEN_CONFIGURATION`

The detector implementation demonstrated change-point capability on the preregistered synthetic sanity stream, but the frozen real-market risk-overlay formulation failed every primary market gate. Nothing migrates to the Factory.

## Frozen evidence

- upstream: `fiannai/bocd`
- upstream SHA: `0c09315e9102ddea885bb7164e47b61a95e99dac`
- workflow run: `35652310062`
- artifact: `gate-btc-bocd-structural-risk-overlay`
- artifact id: `10662487717`
- artifact head SHA: `425e1c5d19934cc8e15d5e322d252d528d20021d`
- market: OKX BTC-USDT spot, 1h
- rows: 8,000 closed candles
- data SHA256: `67aea091e39c1fccee16ecf2b0c58ac3b4bc4d5b7e95ec823832bfeeda875f02`
- resolved decisions: 7,998

## Synthetic sanity

Planted variance-regime breaks: 500 and 1000.

Detected events included 501 and 1006, matching both planted breaks within the preregistered +/-100 tolerance.

`synthetic_sanity = PASS`

This establishes detector capability only; it carries no market-economic credit.

## Real-market outcome

Frozen detector/mapping:

- StudentTModel
- constant hazard = 1/720
- max run length = 2000
- run-length reset threshold > 20
- 24h flat cooldown after event
- 10 bps per position change / 20 bps round trip

Results:

| Metric | Baseline | BOCPD overlay |
|---|---:|---:|
| Final equity | 7,883.41 | 6,197.38 |
| Net return | -21.17% | -38.03% |
| Max drawdown | -49.76% | -51.72% |
| Position changes | 2 | 168 |
| Round-trip equivalent | 1 | 84 |

Detector/event diagnostics:

- market change points detected: **131**
- preregistered acceptable event-count range: 3..100 -> **FAIL**
- post-event 24h volatility enrichment: **1.08304x**
- required enrichment: >=1.25x -> **FAIL**
- relative max-drawdown improvement: **-3.93%** (drawdown worsened)
- required: >=10% -> **FAIL**
- final-equity ratio overlay/baseline: **0.78613**
- required: >=0.98 -> **FAIL**

All four real-market gates failed.

## Scientific disposition

`BOCPD_STRUCTURAL_RISK_OVERLAY = REJECT_FROZEN_CONFIGURATION`

The result does not support this BOCPD formulation as a useful BTC hourly risk overlay. The detector fired too often under the frozen mapping, did not materially enrich subsequent realized volatility, increased drawdown, and materially reduced net equity.

No post-outcome changes are allowed to:

- hazard rate;
- reset threshold;
- cooldown duration;
- Student-t prior;
- observation transform;
- costs;
- pass thresholds;
- data window length.

Any future BOCPD idea must be a new preregistered hypothesis with a materially different scientific question, not a retune of this experiment.

## Factory disposition

Nothing migrates.

BOCPD may remain known as an external change-point research tool, but this risk-overlay formulation is closed and rejected.

Safety boundary remains:

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL=0`
- no engine feed
- no automatic promotion
