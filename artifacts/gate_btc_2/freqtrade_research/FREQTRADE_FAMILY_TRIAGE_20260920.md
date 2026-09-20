# Freqtrade candidate-family triage — isolated research

Date: 2026-09-20

Status: research only. This document is intentionally isolated from the active QRDS Factory. It does not promote, register, or execute any new Factory grammar/family.

Permanent safety boundary:
- RESEARCH_ONLY=true
- SHADOW_ONLY=true
- no live orders
- no capital
- no automatic promotion into Factory
- external reported performance is ignored as evidence

## Decision rule
A source strategy is not imported as-is. We extract only a falsifiable structural hypothesis. Candidate families are classified as:
- ADVANCE: sufficiently distinct and testable to justify an isolated POC later;
- COMPONENT_ONLY: useful execution/risk/filter mechanic, but not an alpha family by itself;
- HOLD: potentially interesting but too entangled/overfit-prone to prioritize;
- REJECT: structurally weak, dimensionally suspect, or only a didactic example.

## Current triage

### FT-HYP-001 — adaptive_execution_slicing
Source: `AlmgrenChrissStrategy.py` @ `70dc625c479e0f88e97c3fedf4c2f544bc8e8775`
Disposition: COMPONENT_ONLY / HIGH VALUE

Structural hypothesis:
Volatility- and liquidity-aware staged execution may reduce execution-risk concentration versus one-shot fills while preserving upstream alpha.

Why it matters:
- separates alpha decision from execution quality;
- contains explicit slice scheduling, position adjustment and partial exits;
- exposes an execution surface QRDS replay currently does not model.

Primary risks:
- execution benefit is market/microstructure dependent;
- backtest fidelity requires realistic fill/impact assumptions;
- should never be credited as alpha.

Next isolated test:
Same upstream entry/exit decisions, one-shot fills versus fixed TWAP versus adaptive slicing, with identical costs and no retuning.

### FT-HYP-002 — volatility_band_mean_reversion
Source: `Bandtastic.py` @ `f7710c76ae1e4ac7aff90857a647e4c2143baf9f`
Disposition: ADVANCE / MEDIUM-HIGH VALUE

Structural hypothesis:
Extreme deviations from multi-width volatility bands, optionally conditioned by momentum/flow state, may define a regime-dependent mean-reversion family.

Why it matters:
- combines distance-from-band severity with optional RSI/MFI/EMA guards;
- naturally supports regime segmentation;
- can be reduced to a small falsifiable grammar instead of importing hyperopt parameters.

Primary risks:
- original strategy exposes a large optimized parameter surface;
- reported historical performance must be ignored;
- likely sensitive to volatility regime, fee level and holding horizon.

Next isolated test:
Rebuild only the structural grammar: normalized band distance + optional momentum/flow gate + symmetric exit. Freeze small parameter grids before data split.

### FT-HYP-003 — candlestick_pattern_event
Source: `PatternRecognition.py` @ `c4c9d2e925a56eba39c9cff31ba532c446818f5d`
Disposition: ADVANCE AS FEATURE FAMILY / MEDIUM VALUE

Structural hypothesis:
Discrete candlestick-pattern events may contain conditional information when treated as features and evaluated by regime rather than accepted as standalone trading folklore.

Why it matters:
- exposes a large categorical event vocabulary;
- can be evaluated cross-sectionally and conditionally;
- useful as feature discovery even if no standalone alpha survives.

Primary risks:
- severe multiple-testing risk across many TA-Lib patterns;
- sparse events;
- easy to overfit pattern identity and direction.

Next isolated test:
Event-study first, not strategy optimization: forward-return distributions after each pattern, PIT-safe, multiple-testing correction, regime conditioning, then only surviving clusters become strategy hypotheses.

### FT-HYP-004 — multi_horizon_ma_lattice
Source: `MultiMa.py` @ `dd398f7f54ddf921678d63329c8612450d2b4bcf`
Disposition: ADVANCE / MEDIUM-HIGH VALUE

Structural hypothesis:
The ordering and spacing of multiple moving-average horizons may encode trend structure more robustly than a single fast/slow crossover.

Why it matters:
- uses a lattice/order relation rather than one crossover;
- maps cleanly to monotonic trend geometry;
- easy to test with low-complexity preregistered families.

Primary risks:
- combinatorial horizon search can explode;
- adjacent moving averages are highly collinear;
- original hyperoptimized values are not evidence.

Next isolated test:
Test monotonic ordering, slope consistency and spacing compression/expansion using fixed logarithmic horizons; compare against a simple EMA20/50 baseline.

### FT-HYP-005 — cross_series_raw_ohlcv_relation
Source: `Diamond.py` @ `fedeb862478aaab58ba18ea069b6a739486c675d`
Disposition: HOLD / LOW-MEDIUM VALUE

Structural hypothesis:
Lagged/scaled relationships among raw OHLCV fields may identify short-lived structural transitions without derived indicators.

Why it is not prioritized:
- very large categorical/lag/scaling search surface;
- arbitrary comparisons such as price fields versus volume can be dimensionally incoherent;
- high risk that hyperopt finds accidental relations.

What can be salvaged:
Only dimensionally normalized variants: returns, range/ATR, normalized volume, lagged rank/percentile relations.

### FT-HYP-006 — volatility_geometry_ratio
Source: `Heracles.py` @ `b4a6331b38fe5e9aec3f2ae6852e0dc917ec1d83`
Disposition: ADVANCE / MEDIUM VALUE

Structural hypothesis:
Ratios between independent volatility/channel descriptors at different lags may encode compression/expansion transitions useful for entry timing.

Why it matters:
- relates Donchian position and Keltner width rather than just absolute volatility;
- lag structure is explicit;
- potentially maps to volatility-regime transition families.

Primary risks:
- original threshold/lag values are hyperoptimized;
- ratio interpretation can become unstable near small denominators;
- needs normalization and robustness across assets/timeframes.

Next isolated test:
Use bounded/standardized channel features, preregister a small lag set, and test whether compression→expansion transitions add information beyond ATR/realized-vol baselines.

### FT-HYP-007 — nonlinear_price_power_pattern
Source: `PowerTower.py` @ `c99cdfe3b2a298dc060d7ea84c5208907c701115`
Disposition: REJECT AS WRITTEN

Reason:
The entry rule compares raw price levels to powers of raw price levels (for example close[t] > close[t-2]^p with p around 3.8). This is not scale invariant and is dimensionally suspect. For prices above 1, exponentiation radically changes scale; behavior changes merely because the asset is quoted in different units.

Salvageable idea:
If revisited, translate the concept into scale-invariant acceleration/convexity of log price or returns. That would be a new hypothesis, not a port of PowerTower.

### FT-HYP-008 — dynamic_risk_reward_overlay
Source: `FixedRiskRewardLoss.py` @ `303225f4c50dfe12708332313ffc42e1a12ed921`
Disposition: COMPONENT_ONLY / HIGH VALUE

Structural hypothesis:
ATR-derived initial risk with break-even migration and fixed-R multiple profit protection can be tested as an exit/risk overlay independent of the alpha signal.

Why it matters:
- cleanly decouples entry alpha from risk management;
- gives QRDS a way to ask whether edge comes from signal or exit geometry;
- naturally supports matched-entry experiments.

Primary risks:
- callback implementation details may differ between historical and live semantics;
- fixed R multiples can truncate convex winners;
- ATR stop placement can be regime sensitive.

Next isolated test:
Hold entries constant. Compare baseline exits versus ATR initial stop, break-even migration and R-multiple protection with identical costs.

### FT-HYP-009 — psar_trailing_exit_overlay
Source: `CustomStoplossWithPSAR.py` @ `bb980d7ac2e0218106f1e918eafd5bd44b2f0102`
Disposition: COMPONENT_ONLY / MEDIUM VALUE

Structural hypothesis:
A stateful PSAR-based trailing exit may improve downside control for selected trend families.

Why it is not an alpha family:
The source itself states its entry rule is nonsensical/example-only. The potentially useful object is the custom trailing-stop mechanism.

Next isolated test:
Apply to a fixed trend-entry stream and compare against static stop, ATR trail and time exit.

### FT-HYP-010 — informative_pair_regime_gate
Source: `InformativeSample.py` @ `665e4f3caf512a7e8ab35cea757ee66b3dd87e26`
Disposition: ADVANCE AS FILTER FAMILY / HIGH VALUE

Structural hypothesis:
A higher-timeframe or reference-asset state can condition lower-timeframe entries and improve regime selectivity.

Why it matters:
- formalizes cross-timeframe/cross-series context;
- BTC can act as a market-state reference for altcoin decisions;
- directly testable as incremental filter value over an unchanged base signal.

Primary risks:
- timestamp alignment/forward-fill leakage;
- false improvement caused by reduced trade count;
- reference pair choice may overfit.

Next isolated test:
Freeze a base strategy, add lag-safe reference-state gates one at a time, and evaluate incremental OOS effect including missed-opportunity cost.

### FT-HYP-011 — combinatorial_indicator_relation_grammar
Source: `GodStra.py` @ `0a8be5c5da31180abb704c188f55757f9c35dac8`
Disposition: HOLD AS META-HYPOTHESIS / HIGH OVERFIT RISK

Structural hypothesis:
A generic grammar of indicator-vs-indicator and indicator-vs-threshold relations can search a broad technical-feature space.

Why it is interesting:
- it is structurally similar to a grammar/factory idea;
- supports relational operators and broad indicator vocabulary.

Why it is dangerous:
- enormous multiple-testing surface;
- easy to rediscover noise with hyperopt;
- imported directly it would overlap/conflict with QRDS Factory design.

Decision:
Do not integrate it into Factory. Keep it external as a benchmark/meta-reference for search-space design only. Any future experiment must compare discovery efficiency under equal trial budgets and strict nested OOS validation.

### FT-HYP-012 — ema_heikinashi_confirmation
Source: `Strategy001.py` @ `352c344fdb07a56274357e1f534206cac8cc4995`
Disposition: HOLD / LOW NOVELTY

Structural hypothesis:
Trend crossover signals may benefit from Heikin-Ashi directional confirmation.

Why low priority:
- conventional EMA crossover plus smoothed-candle confirmation;
- likely overlaps existing trend/filter ideas;
- useful primarily as a control family, not a novel source.

## Current research shortlist

Advance for isolated scientific POC later:
1. volatility_band_mean_reversion
2. multi_horizon_ma_lattice
3. informative_pair_regime_gate
4. volatility_geometry_ratio
5. candlestick_pattern_event (event-study first)

Execution/risk components to test independently of alpha:
1. adaptive_execution_slicing
2. dynamic_risk_reward_overlay
3. psar_trailing_exit_overlay

Hold as research/meta references:
1. cross_series_raw_ohlcv_relation — only after normalization
2. combinatorial_indicator_relation_grammar — external benchmark only
3. ema_heikinashi_confirmation — low novelty control

Reject as written:
1. nonlinear_price_power_pattern / PowerTower

## Boundary with the active Factory
Nothing in this triage is imported into `artifacts/gate_btc_2/factory/`, no active Factory workflow is modified, and no candidate is promoted. This branch is a research notebook in repository form only.
