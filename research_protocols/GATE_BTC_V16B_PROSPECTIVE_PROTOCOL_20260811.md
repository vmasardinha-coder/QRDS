# GATE BTC — V16B_CAUSAL_SHORT — PROSPECTIVE SHADOW PROTOCOL

**Freeze date:** 2026-08-11 BRT  
**Status:** RESEARCH_ONLY=True | SHADOW_ONLY=True | NOT_APPROVED=True | ORDERS=0 | REAL_CAPITAL=0

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
- if required data or execution eligibility is unavailable, status is `BLOCKED` and no synthetic return is appended.

## Frozen signal and model

Features:
`mom7,mom14,mom30,mom60,mom90,residmom7,residmom14,residmom30,residmom60,residmom90,vol14,vol30,vol60,corr30,corr60,beta30,beta60,logvol30`

Point-in-time universe:
- latest CMC Top-150 snapshot available by Thursday signal date;
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
- long leg may use spot or another pre-declared executable instrument; unavailable long = fail closed / block unless an instrument mapping rule is frozen before the signal;
- realized-vol lookback = 13 weeks;
- target annualized vol = 20%;
- max exposure = 1.0x;
- no leverage above 1x;
- turnover cost = 15 bps primary;
- 30 bps and 50 bps are diagnostic stress only, never selection criteria after freeze;
- Binance archived short funding is recorded separately and added to the shadow ledger where the short leg is implemented with USD-M perpetuals, weighted at `0.05 * exposure` per selected short.

## External Delta benchmark discipline

The external Delta is a benchmark, not a tuning target.

Public structural facts that may be used because they were known before freeze:
- weekly rebalance around Friday;
- 10 long / 10 short;
- scans hundreds of cryptoassets;
- seeks strongest/highest-upside assets for longs and weakest/highest-downside assets for shorts.

Known historical return prints, including +7.24% and other May-July 2026 observations, are retrospective withheld-output diagnostics only. They cannot justify any V16B parameter change.

For every new external Delta print received after freeze:
1. seal V16B signal, holdings, exposure, turnover, cost, source coverage and execution eligibility first;
2. seal the corresponding V16B P&L before recording the external Delta result;
3. compare only date-aligned intervals;
4. record external source/screenshot timestamp;
5. never backfill a V16B choice based on the external result.

## Required prospective ledger fields

- signal_date_utc
- entry_date_utc
- exit_date_utc
- candidate_id
- model_hash / code commit
- input-data hashes
- eligible_universe_count
- liquidity-qualified_count
- shortable_count
- longs_10
- shorts_10
- score for each selected asset
- exposure
- trailing_vol
- turnover
- transaction_cost
- short funding by instrument
- gross long P&L
- gross short P&L
- net P&L
- BTC benchmark return
- source coverage / outage state
- status = OK / BLOCKED
- blocker reason
- external Delta print only after V16B row is sealed

## Checkpoints

Interim weekly results are descriptive only.

Formal scientific checkpoints:
- 13 completed prospective weeks: first diagnostic gate;
- 26 completed prospective weeks: stability gate;
- 52 completed prospective weeks: primary evidence gate.

No promotion to capital is authorized by this protocol. Any live proposal requires a separate approval document covering venue mapping, long-side executability, slippage/order-book capacity, margin/liquidation/ADL risk, operational monitoring and explicit capital limits.

## Current verdict at freeze

`PASS_TO_START_PROSPECTIVE_SHADOW`

`LIVE_OR_CAPITAL_APPROVAL=NO`
