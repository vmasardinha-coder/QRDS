# GATE BTC — Phase 2 Profit-Retention Result

Status: **RESEARCH RESULT / CANDIDATE FOR PROSPECTIVE SHADOW ONLY**  
Official workflow run: **31277372106**  
Head: `42ea4542ad941c1ca3195d75208e0d9ef2903420`  
Artifact: `gate-btc-profit-retention-31277372106`  
Artifact id: `9027397831`  
Artifact SHA-256: `e162c492f8188d2a72abf2dea8a6eab6a888fbf687d8a8da9b9ec34de28b9ab4`

## Reproducibility

The official GitHub run passed:

- predeclared exit-policy unit tests;
- download of the pinned Phase-1 #115 artifact;
- Phase-1 protocol / canonical V2A / 444-history-pass integrity guards;
- Phase-2 study execution;
- safety/result contract;
- artifact publication.

Primary sample:

- 62 complete signal months with PIT signal coverage >=95%;
- 1,240 baseline selected-alt trades: 496 Moderada and 744 Ultra;
- entry selections unchanged;
- final incomplete forward month excluded.

## Baseline giveback diagnosis

### QOS Moderada

- mean per-trade MFE: **+28.47%**;
- median MFE: **+12.97%**;
- mean month-end giveback from MFE: **28.58 percentage points**;
- 39.92% of trades reached at least +20%;
- among those +20% trades, **26.77%** finished the monthly boundary at zero or negative;
- mean MFE among +20% trades: **+62.43%**.

### QOS Ultra

- mean per-trade MFE: **+25.77%**;
- median MFE: **+11.76%**;
- mean month-end giveback from MFE: **25.97 percentage points**;
- 37.50% of trades reached at least +20%;
- among those +20% trades, **24.01%** finished the monthly boundary at zero or negative;
- mean MFE among +20% trades: **+58.41%**.

This supports the existence of a material profit-retention problem independent of the Phase-1 entry-selection question.

## Predeclared policy results

The primary metric is paired mean selected-alt-sleeve return delta versus the `MONTH_END` baseline across the same signal months.

### QOS Moderada

- `MONTH_END`: mean sleeve return **-0.1078%/month**;
- `LOCK_50`: **+1.2688%/month**, delta **+1.3766 pp/month**;
  - paired bootstrap 95% interval: **[-0.3007, +3.0854] pp/month**;
  - bootstrap probability delta > 0: **94.76%**;
- `FIXED_14D`: **+1.1497%/month**, delta **+1.2575 pp/month**;
  - bootstrap probability delta > 0: **74.52%**;
- `FIXED_21D`: delta **-2.0997 pp/month**, materially worse than baseline.

### QOS Ultra

- `MONTH_END`: mean sleeve return **-0.2017%/month**;
- `LOCK_50`: **+0.8010%/month**, delta **+1.0027 pp/month**;
  - paired bootstrap 95% interval: **[-0.2397, +2.2614] pp/month**;
  - bootstrap probability delta > 0: **94.30%**;
- `FIXED_14D`: **+0.8041%/month**, delta **+1.0058 pp/month**;
  - bootstrap probability delta > 0: **72.72%**;
- `FIXED_21D`: delta **-1.9752 pp/month**, materially worse than baseline.

The bootstrap intervals still cross zero. These are promising in-sample research results, not proof of a production edge.

## Holding-time interpretation

`LOCK_50` is not an early-exit rule for every trade:

- Moderada: early exit on ~27.82% of trades; mean holding ~25.87 days; median 30 days;
- Ultra: early exit on ~26.08% of trades; mean holding ~26.17 days; median 30 days.

The evidence therefore does **not** support a generic “sell after 7/14 days” rule. The stronger hypothesis is conditional:

> allow the monthly trade to run, but once unrealized profit reaches +20%, stop allowing more than half of the best observed profit to be given back.

`FIXED_14D` remains a secondary challenger because its mean was competitive, but its paired-bootstrap evidence was materially weaker and its rule truncates every trade regardless of path.

## Regime decomposition

Most of `LOCK_50`'s improvement comes from DEFENSIVE periods:

- Moderada DEFENSIVE: `MONTH_END` -1.6145% -> `LOCK_50` +0.9090% per alt sleeve;
- Ultra DEFENSIVE: `MONTH_END` -1.3606% -> `LOCK_50` +0.6442%;
- Moderada RISK_ON: +1.6067% -> +1.6783%;
- Ultra RISK_ON: +1.1171% -> +0.9795%.

This is consistent with Phase 1, where the QOS selector's largest damage appeared in DEFENSIVE periods. It does not establish that an exit overlay repairs the full portfolio alpha.

## Decision

1. **Do not deploy the current QOS selection layer as-is.** Phase 1 did not demonstrate structural positive selection alpha.
2. **Freeze `LOCK_50` as the sole primary profit-retention candidate for future prospective/shadow validation.**
3. Keep `FIXED_14D` as a secondary challenger only; do not tune additional horizons or activation/giveback thresholds on this historical sample.
4. Do not claim `LOCK_50` restores portfolio alpha. The present result is selected-alt-sleeve evidence and remains in-sample.
5. The next scientifically valid confirmation is untouched future/prospective shadow data using the frozen `LOCK_50` definition. Re-slicing this same historical sample to manufacture a holdout after seeing the result would not be an independent validation.

KAITO was not among the QOS selected trades in the >=95% complete-month sample; it is therefore not used as evidence for this result.

Safety: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED`, `ENGINE_FEED=false`, entry selection unchanged, Phase-1 methodology unchanged, orders=0, capital=0.
