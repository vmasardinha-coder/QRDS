# Freqtrade family triage addendum — isolated research

This addendum remains outside the active QRDS Factory.

## FT-HYP-013 — intraday_time_seasonality
Source: `HourBasedStrategy.py` @ `8f0abc74262da360b2cfb8ac853cc83e8376a612`
Disposition: ADVANCE AS EVENT/FILTER STUDY / MEDIUM VALUE

Structural hypothesis:
Crypto return/volatility/liquidity distributions may vary systematically by UTC hour, allowing time-of-day to act as a regime/filter feature rather than a standalone optimized trading rule.

Why it is worth studying:
- crypto trades continuously, so intraday microstructure/participant composition can vary by region/session;
- simple to test without indicator complexity;
- can be evaluated as an incremental filter on fixed signals.

Why the source strategy itself should not be imported:
- it hyperoptimizes buy/sell hour windows directly;
- the reported source results are selection-biased and ignored;
- optimal hour windows can drift with market structure and DST-linked participant behavior.

Next isolated test:
Build a PIT-safe UTC-hour event study first: conditional forward return, volatility, spread/liquidity proxies and trade outcome by hour. Require stability across years/regimes before any filter experiment.

## FT-HYP-014 — break_even_unwind_policy
Source: `BreakEven.py` @ `04fa16497d4c0564d71c260ed8cc47f6aa773e4d`
Disposition: COMPONENT_ONLY / LOW-MEDIUM VALUE

Structural hypothesis:
When a system is intentionally de-risking or shutting down, a time-dependent break-even/near-break-even unwind policy may reduce residual exposure compared with waiting indefinitely for normal strategy exits.

Interpretation:
This is operational position-management policy, not alpha. It has no entry signal and is explicitly designed to unwind existing positions.

Potential use:
- shadow/live operational safety studies;
- controlled shutdown or strategy retirement;
- compare immediate liquidation versus staged break-even unwind under explicit risk limits.

Primary risk:
Waiting for break-even can increase time-in-risk and create loss aversion mechanically. Any test must include maximum holding time and tail-loss constraints.

## Updated shortlist

Advance as alpha/feature/filter studies:
1. volatility_band_mean_reversion
2. multi_horizon_ma_lattice
3. informative_pair_regime_gate
4. volatility_geometry_ratio
5. candlestick_pattern_event
6. intraday_time_seasonality

Execution/risk components:
1. adaptive_execution_slicing
2. dynamic_risk_reward_overlay
3. psar_trailing_exit_overlay
4. break_even_unwind_policy

Hold/meta:
1. cross_series_raw_ohlcv_relation
2. combinatorial_indicator_relation_grammar
3. ema_heikinashi_confirmation

Reject as written:
1. nonlinear_price_power_pattern
