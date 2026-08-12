# GATE BTC — V16B_CAUSAL_SHORT — PROSPECTIVE SHADOW PROTOCOL

**Freeze date:** 2026-08-11 BRT  
**Status:** RESEARCH_ONLY=True | SHADOW_ONLY=True | NOT_APPROVED=True | ORDERS=0 | REAL_CAPITAL=0 | ENGINE_FEED=False

## Candidate

`GATE_BTC_V16B_CAUSAL_SHORT_LIQ10_VOL20_FREEZE_20260811`

Parent discovery line: cross-sectional extreme classifier, weekly 10 long / 10 short, point-in-time Top-150 universe, fixed USD 10m/day 30d-volume floor, causal Binance USD-M shortability, 20% vol target capped at 1x, 15 bps turnover cost.

No parameter may be changed because of any external Delta checkpoint.

## Prospective clock

The 2025-2026 retrospective window is **not** true untouched OOS because the research process had already inspected the regime while testing earlier candidate families. It is validation-after-design only.

True untouched V16B evidence begins after this freeze:

- first eligible signal: **Thursday 2026-08-13 UTC close**;
- first eligible entry: **Friday 2026-08-14 UTC close**;
- first complete weekly return: **Friday 2026-08-21 UTC close**;
- no historical/backfilled decision may count as prospective;
- if required data or execution eligibility is unavailable, status is `BLOCKED` and no synthetic economics are appended.

## Frozen signal and model

Features:
`mom7,mom14,mom30,mom60,mom90,residmom7,residmom14,residmom30,residmom60,residmom90,vol14,vol30,vol60,corr30,corr60,beta30,beta60,logvol30`

Point-in-time universe:
- latest CMC Top-150 snapshot demonstrably available by Thursday signal close;
- existing PIT source/identity policy;
- complete feature row required;
- `logvol30 = log1p(median of the last 30 source-specific volume_usd observations)` and the eligibility threshold remains effectively USD 10,000,000;
- no use of current-survivor membership.

Target used for expanding historical training:
- bottom 10% next-week raw return = class 0;
- middle 80% = class 1;
- top 10% = class 2.

Model:
- `HistGradientBoostingClassifier`;
- learning_rate = 0.05;
- max_iter = 100;
- max_depth = 2;
- min_samples_leaf = 50;
- l2_regularization = 10.0;
- random_state = 20260811;
- score = `P(top10%) - P(bottom10%)`;
- expanding training;
- minimum 52 fully realized weeks;
- retrain every 13 weeks.

## Frozen portfolio

- signal Thursday, execution Friday;
- 10 longs, equal weighted;
- 10 shorts, equal weighted;
- unscaled gross = +0.50 / -0.50;
- short candidate must pass causal Binance USD-M eligibility at Friday execution;
- long leg may use spot or another pre-declared executable instrument; unavailable selected long = fail closed / block, not post-ranking replacement;
- realized-vol lookback = 13 weeks;
- target annualized vol = 20%;
- max exposure = 1.0x;
- no leverage above 1x;
- turnover cost = 15 bps primary;
- 30 bps and 50 bps are diagnostic stress only, never selection criteria after freeze;
- Binance archived short funding is recorded separately and added where the short leg uses USD-M perpetuals, weighted at `0.05 * exposure` per selected short.

## Staged prospective evidence chain — Amendment A2

Before the first eligible prospective signal, the audit contract was strengthened by `GATE_BTC_V16B_AUDIT_AMENDMENT_A2_20260811`. Prospective count was zero. **No economic methodology, model, feature, portfolio, liquidity, shortability, exposure, volatility-target or cost parameter changed.**

The append-only evidence chain is now mandatory:

1. **`V16B_SIGNAL_SEAL`** — created after Thursday UTC close and before Friday UTC close. It seals model/code/input hashes, CMC snapshot ID and demonstrated availability timestamp, feature-panel hash, model-state hash, complete eligible score map, deterministic complete score ranking and the preliminary top-10 longs. The longs must be exactly the first 10 names in that ranking.
2. **`V16B_ENTRY_SEAL`** — created before Friday UTC close and referencing the exact signal seal. Longs cannot change. Each selected long requires predeclared executability evidence. Shortability must be checked in the frozen ranking from worst score upward; shorts must be the first 10 causally shortable names encountered, and checking stops on the 10th. Instruments, exposure, trailing volatility, turnover estimate and the frozen 15 bps cost assumption are sealed here.
3. **`V16B_RESULT_SEAL`** — created only after the following Friday UTC close and referencing the exact entry seal. It must contain source/execution hashes plus per-asset entry/exit prices, raw returns, frozen weights and weighted P&L for exactly the 20 sealed holdings. Gross long, gross short, funding, cost, net P&L and BTC return are recomputed from those components.
4. **`EXTERNAL_DELTA_ATTACHMENT`** — permitted only after the result seal. It references that result hash and cannot modify any earlier self evidence.

The legacy one-stage self-result seal is disabled.

## External Delta benchmark discipline

The external Delta is a benchmark, not a tuning target.

Public structural facts known before freeze may be used:
- weekly rebalance around Friday;
- 10 long / 10 short;
- scans hundreds of cryptoassets;
- seeks strongest/highest-upside assets for longs and weakest/highest-downside assets for shorts.

Known historical return prints, including +7.24% and other May-July 2026 observations, are retrospective withheld-output diagnostics only. They cannot justify any V16B parameter change.

For every new external Delta print received after freeze:
1. complete and seal `V16B_SIGNAL_SEAL`;
2. complete and seal `V16B_ENTRY_SEAL` before entry close;
3. complete and seal `V16B_RESULT_SEAL` after exit close;
4. only then attach the external Delta print;
5. compare only date-aligned intervals and retain source timestamp/reference;
6. never backfill a V16B choice based on the external result.

## Required prospective evidence

Signal stage must preserve the complete eligible ranking, not only selected assets. Entry stage must preserve causal shortability checks in rank order and exact instrument mapping. Result stage must preserve per-asset economics for all 20 holdings plus actual funding, cost and BTC benchmark inputs. Every stage is append-only and SHA-256 sealed.

A `BLOCKED` stage may carry the blocker and source evidence needed to explain the failure but may not carry synthetic holdings/economics inconsistent with the stage contract.

## Historical replay auditability

The reconstructed 11-week 2026 print (+7.3356% ex funding; +7.3914% with audited funding) remains **reference-only and non-prospective**. The detailed replay file referenced by SHA-256 has not been recovered from the Git tree or recovered Actions packages, so it is not promotion evidence and cannot support a mechanism-identity claim versus external Delta. See `artifacts/gate_btc/v16b/GATE_BTC_V16B_HISTORICAL_REPLAY_AUDITABILITY_20260811.json`.

## Checkpoints

Interim weekly results are descriptive only.

Formal scientific checkpoints:
- 13 completed prospective weeks: first diagnostic gate;
- 26 completed prospective weeks: stability gate;
- 52 completed prospective weeks: primary evidence gate.

No promotion to capital is authorized by this protocol. Any live proposal requires a separate approval document covering venue mapping, long-side executability, slippage/order-book capacity, margin/liquidation/ADL risk, operational monitoring and explicit capital limits.

## Current verdict

`PASS_TO_START_PROSPECTIVE_SHADOW_FAIL_CLOSED`

`LIVE_OR_CAPITAL_APPROVAL=NO`
