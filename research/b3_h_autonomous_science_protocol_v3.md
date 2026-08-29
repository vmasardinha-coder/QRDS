# GATE BTC B3 Autonomous Science Protocol v3

Status: PREREGISTERED_BEFORE_ANY_V3_ECONOMICS
Issue: #289

Purpose: continue the autonomous B3 scientific factory only after the finite v1/v2 OHLCV-derived grammar is exhausted at H2729, using a materially distinct observed-data mechanism dimension. V3 must not clone, rename, retune or outcome-guide any v1/v2 family.

## Boundary and inheritance

Protocols v1/v2 remain immutable for H170-H2729. Their rejection ledger, economics, costs, execution timing, cutoff, discovery/replication windows and survivor gates remain authoritative for those families and are never reopened by v3.

V3 begins at H2730 only after its source contract, deterministic family identities and CI safety/non-duplication checks are frozen. No v3 economics may run while source qualification is incomplete.

## Materially distinct data dimension

V3 uses official B3 trade/tick microstructure observations rather than session OHLCV-derived features. Primary scientific source must be official B3 raw trade/tick data with auditable provenance. MT5, if available and separately qualified, is secondary cross-validation only and never primary truth.

The fixed v3 feature universe is:

1. `EARLY_TRADE_COUNT_RATE`: trades per elapsed minute inside the decision window.
2. `EARLY_MEDIAN_TRADE_SIZE`: median observed trade quantity inside the decision window.
3. `LARGE_TRADE_VOLUME_SHARE`: share of decision-window traded quantity contributed by trades whose quantity is above the causal prior-session 90th percentile trade-size reference.
4. `INTERTRADE_DURATION_CV`: coefficient of variation of positive inter-trade durations inside the decision window.
5. `PRICE_CHANGE_SIGN_IMBALANCE`: `(up_tick_count - down_tick_count) / (up_tick_count + down_tick_count)` using consecutive distinct trade prices inside the decision window; zero-price-change pairs are excluded from the denominator.

These definitions are frozen before economics. If official source schema cannot support an exact feature, that feature is `DATA_GAP` and must not be silently proxied or replaced.

## Deterministic family grammar

Fixed order:

- features: exactly the five listed above, in listed order;
- directions: `CONTINUATION`, `REVERSION`;
- decision windows: 15, 30, 60, 90 minutes;
- absolute robust-z thresholds: 0.75, 1.00, 1.25, 1.50;
- holding horizons evaluated inside each family: 30, 60, 120 minutes;
- standardization lookback: exactly 20 prior eligible sessions, inherited from original v1 causal standardization and not selected from v1/v2 outcomes.

Cartesian ordering is feature -> direction -> decision window -> threshold. This creates exactly 160 v3 family identities, mapped sequentially H2730-H2889, or sixteen generations of ten. The grammar is finite. H2890+ is unauthorized unless a later protocol is separately preregistered before economics.

A v3 identity is the tuple `(protocol=v3, data_dimension=TICK_MICROSTRUCTURE, feature, direction, decision_window_minutes, abs_z_threshold, standardization_lookback_sessions=20)`. Because `protocol/data_dimension/feature` differ from v1/v2 identities, no v3 identity can equal an exhausted v1/v2 identity.

## Causal references

Current-session observations never enter their own reference distribution. Robust z-score uses exactly the immediately prior 20 finite eligible-session values: median center and `1.4826 * MAD` scale. Fewer than 20 prior finite values or zero MAD yields no signal.

For `LARGE_TRADE_VOLUME_SHARE`, the trade-size 90th percentile reference is calculated only from trades in the immediately prior 20 eligible sessions, using the same instrument/front-contract identity policy frozen for the generation. The current session cannot define its own large-trade cutoff.

No forward fill, interpolation, synthetic backfill or late reconstruction is allowed.

## Source and identity requirements

Before evaluation, the source qualifier must prove and persist for each required instrument/session:

- provider and source product/file identity;
- immutable raw identifier and SHA-256 of bytes actually used;
- raw schema and parser version;
- timezone/date/session semantics;
- instrument and contract identity including roll/front-contract mapping;
- coverage start/end and missingness;
- duplicate policy and deterministic dedupe result;
- monotonic/nondecreasing event-time QA as appropriate;
- quantity/price domain QA;
- causal publication/availability evidence relative to the historical test;
- explicit distinction between official primary evidence and secondary mirrors.

Schema ambiguity, missing quantity/timestamp fields, unresolved contract identity or inadequate causal coverage fails closed as `DATA_GAP`/`SOURCE_QA_FAIL`; it is never converted into `NO_TRADES`.

## NO_TRADES diagnostic

A family may be classified `NO_TRADES` only after source QA for all required input sessions passes and the exact frozen feature pipeline produces finite causal feature values. Diagnostics must distinguish at least:

- `VALID_RARITY_NO_THRESHOLD_CROSS`;
- `INSUFFICIENT_CAUSAL_LOOKBACK`;
- `ZERO_MAD_REFERENCE`;
- `SOURCE_DATA_GAP`;
- `SCHEMA_QA_FAIL`;
- `CONTRACT_IDENTITY_FAIL`;
- `FEATURE_UNDEFINED_FROM_VALID_INPUT`.

Only the first category is a legitimate scientific no-trade terminal. None may cause threshold changes.

## Economics and replication

Unless a future separately preregistered v3 amendment is required strictly by the new observed-data mechanics, v3 inherits unchanged:

- discovery sessions: 2022-2024;
- independent replication: 2020-2021;
- cutoff exclusive: 2026-08-10;
- reference cost 2 bp, stress cost 3 bp;
- one-extra-bar delayed entry gate;
- holding horizons 30/60/120 minutes;
- minimum-trade, side-stability, calendar-half-stability and concentration gates;
- survivor requires at least two qualified holding-horizon cells in both discovery and independent replication;
- at most two survivors, selected by ascending family id only, never performance rank.

H1 economics and all prospective partial economics remain unread and cannot influence v3 construction or evaluation.

## Loop semantics

Each generation contains exactly ten consecutive families. Persist the complete ten-family preregistration before any evaluation. A no-survivor terminal advances automatically to the next v3 decade. A survivor terminal freezes the survivor and routes it to a separate blind append-only prospective ledger; discovery may continue only according to the factory's frozen survivor/continuation policy and never from partial prospective feedback.

## Safety

`RESEARCH_ONLY=true`
`SHADOW_ONLY=true`
`NOT_APPROVED=true`
`ENGINE_FEED=false`
`ORDERS=0`
`REAL_CAPITAL=0`
`NO_RETUNE=true`
`NO_BACKFILL=true`
`NO_COUNTER_RESET=true`
`FAIL_CLOSED=true`
`H1_ECONOMICS_READ=false`

V3 cannot start economics until source qualification and deterministic identity/non-duplication CI are green.