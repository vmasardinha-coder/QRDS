# Freqtrade candidate-family test closeout — 2026-09-21

Status: isolated research only. No active Factory integration.

Safety boundary:
- RESEARCH_ONLY=true
- SHADOW_ONLY=true
- Factory modified: no
- no live orders or capital
- no automatic family promotion

Dataset used: OKX 1h, 2025-06-01 through 2026-09-21, BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT. Screening comparisons used a conservative 20 bps round-trip cost.

## Scientific disposition after two test stages

### 1. multi_horizon_ma_lattice — ADVANCE TO DEEPER ISOLATED POC
This was the strongest structural family in the first battery and remained positive under horizon-ladder perturbations.

Most convincing case: SOL/USDT.
- fast 6/12/24/48 ladder: +0.307% mean net at 24h; positive in both OOS halves (+0.031%, +0.578%); still +0.107% at 40 bps cost.
- base 8/16/32/64: +0.243%; positive in both OOS halves; +0.043% at 40 bps.
- slow 12/24/48/96: +0.258%; positive in both OOS halves; +0.058% at 40 bps.

ETH also stayed positive across all three ladders at 20 bps, but the fast/base variants were negative in the first OOS half and stronger in the second. XRP was positive overall for fast/base ladders but negative in the first OOS half. BTC did not show economically robust net benefit at 20–40 bps.

Decision: continue with SOL as the primary isolated POC target; ETH as secondary replication. Do not promote to Factory.

### 2. informative_pair_regime_gate — HOLD FOR REPLICATION
On XRP, the BTC reference-state gate improved the fixed EMA-cross base under three of four preregistered gates:
- 4h SMA20: +0.666 percentage-point incremental mean net; N=21 gated events.
- 4h SMA50: +0.554 pp; N=19.
- 12h SMA20: +0.489 pp; N=15.
- 12h SMA50: -0.068 pp; N=20.

The directional consistency across three gates is interesting, but samples are too small for promotion or strong inference.

Decision: replicate on a longer history and broader altcoin panel before any further claim.

### 3. candlestick_pattern_event — HOLD / WEAK
SOL was the only symbol with positive first-stage evidence. Component decomposition showed:
- 24h effects small (+0.020% to +0.112% net).
- 48h effects larger (+0.362% to +0.567%).
- all three patterns were negative in OOS half 1 and positive in half 2.

Decision: no standalone alpha claim. Keep only as an event-feature research candidate. A future test should use longer history, multiple-testing correction, regime conditioning and cluster-level rather than individual-pattern interpretation.

### 4. volatility_band_mean_reversion — DO NOT ADVANCE IN CURRENT FORM
No positive OOS evidence on BTC, ETH or SOL; XRP was only weakly positive (+0.017% net).

Decision: current preregistered formulation does not justify deeper work.

### 5. volatility_geometry_ratio — REJECT CURRENT FORMULATION
All four tested symbols were negative after cost, with particularly poor ETH/XRP outcomes.

Decision: reject this concrete formulation. Any future revisit must be a newly specified compression/expansion hypothesis, not a retune of this failed rule.

### 6. intraday_time_seasonality — REJECT CURRENT FORMULATION
All four assets failed the validation split before final test interpretation.

Decision: stop this formulation; no post-hoc hour retuning.

## Current isolated research queue

Advance:
1. SOL multi_horizon_ma_lattice — deeper POC.
2. ETH multi_horizon_ma_lattice — replication.

Hold / replicate:
1. XRP informative_pair_regime_gate — longer history + larger asset panel.
2. candlestick_pattern_event — feature/event study only.

Stop current formulations:
1. volatility_band_mean_reversion.
2. volatility_geometry_ratio.
3. intraday_time_seasonality.

## Boundary
Nothing in this closeout changes `artifacts/gate_btc_2/factory/`, existing Factory grammars, Factory runtime, or production/shadow routing. The research remains on `research/freqtrade-family-tests` only.
