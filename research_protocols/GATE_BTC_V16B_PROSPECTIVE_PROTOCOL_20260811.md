# GATE BTC — V16B_CAUSAL_SHORT — PROSPECTIVE SHADOW PROTOCOL

**Freeze date:** 2026-08-11 BRT  
**Status:** RESEARCH_ONLY=True | SHADOW_ONLY=True | NOT_APPROVED=True | ORDERS=0 | REAL_CAPITAL=0 | ENGINE_FEED=False

## Candidate

`GATE_BTC_V16B_CAUSAL_SHORT_LIQ10_VOL20_FREEZE_20260811`

Frozen economics remain unchanged: point-in-time CMC Top-150 universe; effective USD 10m/day 30d-volume floor; 18 frozen features; HistGradientBoostingClassifier; weekly Thursday signal / Friday entry; 10 equal longs / 10 equal shorts; unscaled gross +0.50/-0.50; 13-week realized-vol lookback; 20% annualized target; exposure capped at 1.0x; 15 bps turnover cost; actual USD-M short funding.

**No external Delta checkpoint may change any candidate parameter.**

## Prospective clock

The 2025-2026 reconstructed window is not untouched OOS and never counts as prospective.

- first eligible signal: **2026-08-13 UTC close**;
- first eligible entry: **2026-08-14 UTC close**;
- first eligible exit: **2026-08-21 UTC close**;
- prospective count at adoption of Amendments A2-A6: **0**;
- missing/late/ambiguous evidence fails closed; no synthetic return or zero funding is created.

## Frozen model

Features: `mom7,mom14,mom30,mom60,mom90,residmom7,residmom14,residmom30,residmom60,residmom90,vol14,vol30,vol60,corr30,corr60,beta30,beta60,logvol30`.

Target: bottom 10% next-week raw return = class 0; middle 80% = class 1; top 10% = class 2.

Model: HistGradientBoostingClassifier; learning_rate 0.05; max_iter 100; max_depth 2; min_samples_leaf 50; l2_regularization 10; random_state 20260811; score `P(top10%)-P(bottom10%)`; expanding training; at least 52 fully realized weeks; refit every 13 scoring weeks.

## Append-only evidence chain

Before the first prospective observation, audit-only Amendments A2-A6 strengthened evidence provenance without changing economic methodology.

1. **`V16B_SIGNAL_SEAL`** — after Thursday UTC close and before Friday UTC close.
2. **`V16B_ENTRY_SEAL`** — before Friday UTC close and referencing the exact signal seal.
3. **`V16B_RESULT_SEAL`** — after the following Friday UTC close and referencing the exact entry seal.
4. **`EXTERNAL_DELTA_ATTACHMENT`** — only after the result seal.

The legacy one-stage result seal is disabled.

## Thursday SIGNAL evidence

The signal builder may use only information demonstrably available by Thursday UTC close. The feature panel cannot contain rows after signal date, and shortability supplied to the signal engine must be strictly historical.

A raw CMC universe snapshot plus a separate evidence manifest are mandatory. The evidence manifest carries snapshot identity, source reference, availability timestamp and the raw snapshot SHA-256. The raw hash is recomputed and both files are sealed in the signal inputs.

The signal seals the entire eligible score map plus **two independently preserved rankings**: `long_ranking_desc` and `short_ranking_asc`. One ranking is never manufactured by reversing the other. The top-10 longs and the risk state (exposure, trailing volatility, prior weights) are sealed at this stage. Friday shortability and external Delta are not inspected.

## Friday ENTRY evidence

The entry stage references the exact signal-seal hash. Binance Spot and USD-M public exchangeInfo payloads are hash-bound, and both must carry `serverTime` on/after signal-seal creation and strictly before Friday UTC close.

Selected longs require predeclared Binance Spot USDT TRADING instruments. If a frozen long is unavailable, the week BLOCKS rather than replacing it.

Shortability is checked in exact sealed `short_ranking_asc` order. The shorts are the first 10 verifiably shortable Binance USD-M perpetual names encountered, checking stops at the 10th, and no discretionary replacement is allowed. Any long/short overlap BLOCKS explicitly.

The entry seal freezes exact instruments, exposure, trailing volatility, turnover estimate and the 15 bps cost assumption.

## RESULT evidence — Amendment A6

The weekly result is not typed in manually. It is reconstructed deterministically from preserved raw evidence.

### Prices

`tools/gate_btc_v16b_prospective_prices.py` downloads the entry-day and exit-day 1d archives for every exact sealed instrument: Binance Spot for longs, Binance USD-M for shorts, plus BTCUSDT Spot for the benchmark. Every archive must match its adjacent Binance Data Vision `.CHECKSUM`, and the raw ZIP/checksum files are preserved.

`tools/gate_btc_v16b_prospective_result.py` re-hashes and **reparses those raw ZIPs**. The manifest close and timestamps must equal the contents of the preserved archive.

### Funding

`tools/gate_btc_v16b_prospective_funding.py` collects the required Binance USD-M fundingRate archives, verifies adjacent `.CHECKSUM` files and preserves raw archives. If a required archive is not yet published, the result remains pending/fail-closed; funding is never replaced with zero.

The result builder reparses the raw funding archives and independently recomputes event count, `funding_rate_sum`, first event and last event for each exact selected short. Any disagreement with the audit CSV fails closed.

Funding contribution per short remains the frozen formula `0.05 * exposure * funding_rate_sum`; positive funding benefits the short.

### Economics

For each of the 20 sealed holdings:

- raw return = `exit_close / entry_close - 1`;
- long weight = `+0.05 * sealed exposure`;
- short weight = `-0.05 * sealed exposure`;
- gross long/short PnL = sum of weighted per-asset returns;
- transaction cost = `0.0015 * sealed turnover`;
- net PnL = gross long + gross short + realized short funding - transaction cost;
- BTC benchmark = BTCUSDT Spot exit close / entry close - 1.

The existing `V16B_RESULT_SEAL` validator recomputes these formulas again before accepting the row.

## External Delta discipline

External Delta is benchmark evidence only. Known historical prints, including +7.24%, cannot justify any V16B change.

A Delta print may be attached only after the corresponding V16B result has been sealed. It references the result hash and cannot alter signal, holdings, instruments, exposure or economics.

## Historical validation print

The reconstructed 11-week 2026 print (+7.3356% ex funding; +7.3914% with audited funding) remains **REFERENCE_ONLY_UNREPRODUCED** because its detailed historical replay file was not recovered. It is not promotion evidence and cannot support a mechanism-identity claim versus external Delta.

See `artifacts/gate_btc/v16b/GATE_BTC_V16B_HISTORICAL_REPLAY_AUDITABILITY_20260811.json`.

## Scientific checkpoints

- weekly interim: descriptive only;
- 13 completed prospective weeks: first diagnostic gate;
- 26 completed weeks: stability gate;
- 52 completed weeks: primary evidence gate.

No capital/live promotion is authorized by this protocol.

## Current verdict

`PASS_TO_START_PROSPECTIVE_SHADOW_FAIL_CLOSED`

`LIVE_OR_CAPITAL_APPROVAL=NO`
