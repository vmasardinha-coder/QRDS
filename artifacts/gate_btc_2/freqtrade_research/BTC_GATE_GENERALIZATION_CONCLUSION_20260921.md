# BTC regime-gate generalization conclusion — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true  
Factory touched: **NO**

## Frozen hypothesis

Without per-asset retuning:

- alt entry: fresh EMA20 > EMA50 crossover on 1h close;
- exit: fixed 48h hold;
- round-trip cost in panel research: 0.20%;
- regime gate: BTC 12h close > SMA20;
- no live orders, no capital, no Factory registration/promotion.

## Multi-alt panel

Eight out-of-sample generalization assets were tested in addition to the original XRP case.

| Asset | Ungated mean/trade | Gated mean/trade | Delta | Ungated PF | Gated PF | WF delta positive |
|---|---:|---:|---:|---:|---:|---:|
| ETH | -0.12% | +0.46% | +0.59 pp | 0.93 | 1.43 | 3/5 |
| SOL | +0.09% | -0.22% | -0.31 pp | 1.07 | 0.85 | 3/4 |
| DOGE | -0.38% | +0.48% | +0.86 pp | 0.81 | 1.28 | 3/5 |
| ADA | -0.39% | -1.11% | -0.73 pp | 0.84 | 0.65 | 1/5 |
| LINK | -0.94% | -0.08% | +0.87 pp | 0.59 | 0.95 | 3/5 |
| AVAX | +0.56% | +0.97% | +0.41 pp | 1.40 | 2.09 | 3/5 |
| DOT | -0.70% | -0.46% | +0.24 pp | 0.79 | 0.83 | 4/5 |
| LTC | -0.58% | -0.76% | -0.18 pp | 0.66 | 0.49 | 3/4 |

Panel-level facts:

- positive delta mean: 5/8 assets;
- positive gated mean and PF > 1: 3/8 assets (ETH, DOGE, AVAX);
- majority-positive walk-forward delta: 7/8 assets;
- therefore the gate often removes damaging trades, but does not universally create positive expectancy.

## External Freqtrade execution audit

Same rule, same date range, explicit fees/fills, fixed 48h exit, exact gated-vs-ungated comparison.

### ETH/USDT

- ungated: 63 trades, -1.62% account return, PF 0.85, Sharpe -0.23, max account underwater 3.32%;
- gated: 21 trades, +0.43% account return, PF 1.16, Sharpe +0.06, max account underwater 1.53%;
- incremental account-return delta: +2.05 percentage points;
- lookahead: No bias, 20 tested signals, 0 biased entry/exit signals.

### DOGE/USDT

- ungated: 62 trades, -3.09% account return, PF 0.75, Sharpe -0.35, max account underwater 4.62%;
- gated: 29 trades, +1.41% account return, PF 1.31, Sharpe +0.15, max account underwater 1.77%;
- incremental account-return delta: +4.50 percentage points;
- lookahead: No bias, 20 tested signals, 0 biased entry/exit signals.

Original XRP Freqtrade audit also changed the same ungated baseline from negative to positive with the frozen BTC gate.

## Pooled selection-effect test

The executable baseline event stream was selected first with 48h non-overlap, then split into BTC-gate accepted/rejected events across XRP + 8 generalization assets.

- accepted events: n=233, mean=-0.296%, PF 0.845;
- rejected events: n=321, mean=-0.410%, PF 0.804;
- observed pooled accepted-minus-rejected mean delta: +0.113 percentage points per trade;
- assets with positive accepted-minus-rejected delta: 6/9;
- stratified one-sided permutation p-value: 0.3651.

The pooled effect is **not statistically significant** under this frozen cross-asset test. The gate is therefore **not supported as a universal altcoin filter**.

## Scientific classification

### Rejected claim

> “BTC 12h/SMA20 is a generally positive filter for EMA20/50 trend entries across altcoins.”

The evidence does not support this universal statement.

### Surviving narrower observation

The exact frozen gate materially improved the tested EMA20/50 + 48h setup in XRP, ETH and DOGE, and improved quality/risk in AVAX. These are asset-conditioned research observations, not a universal family rule.

## Decision

- **Do not promote a universal BTC-regime-gate family to Factory.**
- Keep XRP / ETH / DOGE as isolated `KEEP_RESEARCH_SHADOW` candidates.
- Keep AVAX as `KEEP_RESEARCH_RISK_FILTER` candidate, because the ungated setup was already positive and the gate improved mean/PF/drawdown but reduced opportunity count/total return.
- SOL / ADA / LTC: reject this frozen gate for the tested setup.
- LINK / DOT: gate improves damage but remains negative; reject as alpha under this rule.
- No retuning of the BTC timeframe/SMA or alt parameters is authorized by this result; any such change would be a new hypothesis and must restart validation from scratch.

## Boundary

This study remains entirely on `research/freqtrade-family-tests`. No Factory candidate was promoted, no production/shadow runtime was modified, and no live-capital path was enabled.
