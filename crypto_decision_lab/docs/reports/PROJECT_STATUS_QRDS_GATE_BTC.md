# QRDS/QOS Gate BTC — Project Status

Updated at: 2026-07-04T18:36:10.467836+00:00

## Current posture

- Mode: `INTERACTIVE_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- No trading signals, recommendations, allocation decisions, safe-apply, real orders, or canonical promotion.
- Canonical data writes remain `0`.

## Source/data status

| Area | Gate | Ready/Status | Rows/Notes |
|---|---|---:|---|
| Phase 12 Binance public data certification | `PHASE12_PUBLIC_DATA_RESEARCH_READY_CERTIFIED_RESEARCH_ONLY` | `True` |  |
| Phase 13 Binance research backtest baseline | `PHASE13_RESEARCH_BACKTEST_BASELINE_READY_RESEARCH_ONLY` | `True` | 15000 |
| Phase 13 Hyperliquid public adapter | `PHASE13_HYPERLIQUID_PUBLIC_DATA_ADAPTER_READY_RESEARCH_ONLY` | `True` | 15000 |
| Phase 13 Binance x Hyperliquid comparison | `PHASE13_BINANCE_HYPERLIQUID_SOURCE_COMPARISON_READY_RESEARCH_ONLY` | `True` | 4981 |
| Phase 14 Bybit public adapter | `PHASE14_BYBIT_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY` | `False` |  / PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY |
| Phase 14 OKX public adapter | `PHASE14_OKX_PUBLIC_DATA_ADAPTER_READY_RESEARCH_ONLY` | `True` | 15000 / PUBLIC_ENDPOINT_ACCESS_OK_RESEARCH_ONLY |
| Phase 15 Multi-source trust registry | `PHASE15_MULTISOURCE_TRUST_REGISTRY_COMPARISON_READY_RESEARCH_ONLY` | `True` | 4979 / ready_sources=BINANCE_SPOT,HYPERLIQUID_PERP,OKX_SWAP |
| Phase 16 Multi-source consensus baseline | `PHASE16_MULTISOURCE_CONSENSUS_BASELINE_READY_RESEARCH_ONLY` | `True` | 14937 / ready_sources=BINANCE_SPOT,HYPERLIQUID_PERP,OKX_SWAP / excluded=BYBIT_LINEAR |
| Phase 17 Consensus quality drift monitor | `PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_READY_RESEARCH_ONLY` | `True` | 14937 |

## Current approved stack

1. Binance public spot data certified.
2. Binance research backtest baseline certified.
3. Hyperliquid public perps adapter certified.
4. Binance x Hyperliquid source comparison certified.
5. OKX public swap adapter certified when depth extension is ready in the local run.
6. Bybit adapter implemented but pending external/IP access.
7. Multi-source trust registry certified with Bybit pending.
8. Multi-source consensus baseline certified.
9. Consensus quality/drift monitor status follows latest Phase 17 gate.

## Next technical direction

- If Phase 17 is READY: build research feature layer / regime diagnostics on consensus data.
- If Phase 17 is NEEDS_REVIEW: inspect dispersion/outlier gates before adding new feature layers.
- Keep documentation updates bundled into larger sprint/hotfix packages instead of separate packages.

## Latest Phase 18 update

Updated at: 2026-07-04T19:01:19.171895+00:00

- Phase 18 gate: `PHASE18_RESEARCH_FEATURE_REGIME_DIAGNOSTICS_READY_RESEARCH_ONLY`
- Feature/regime diagnostics ready: `True`
- Feature rows total: `14937`
- Min feature rows per coin: `4979`
- Min mature feature rows per coin: `4812`
- Diagnostic labels are signals: `False`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Diagnostic labels are research-only descriptors, not trading signals, recommendations, allocations, or operational decisions.

## Latest Phase 19 update

Updated at: 2026-07-04T19:11:34.876295+00:00

- Phase 19 gate: `PHASE19_OFFLINE_EXPERIMENT_HARNESS_READY_RESEARCH_ONLY`
- Offline experiment harness ready: `True`
- Eligible rows total: `14364`
- Min eligible rows per coin: `4788`
- Target horizon hours: `24`
- Prediction rows generated: `0`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

The harness contains research targets and chronological splits only. It does not train models or generate predictions, signals, recommendations, allocations, or operational decisions.

## Latest Phase 20 update

Updated at: 2026-07-04T19:28:25.804218+00:00

- Phase 20 gate: `PHASE20_BASELINE_METRICS_NULL_MODELS_READY_RESEARCH_ONLY`
- Baseline metrics ready: `True`
- Baseline metric rows total: `117`
- Baseline families count: `13`
- Model training run: `False`
- Model predictions generated: `0`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 20 establishes null/baseline metrics only. It does not train a model or generate model predictions, signals, recommendations, allocations, or operational decisions.

## Latest Phase 21 update

Updated at: 2026-07-04T19:58:47.027384+00:00

- Phase 21 gate: `PHASE21_BASELINE_AUDIT_INTERPRETABLE_MODEL_BENCHMARK_READY_RESEARCH_ONLY`
- Phase 20 audit ready: `True`
- Interpretable model benchmark ready: `True`
- Model count: `5`
- Model metric rows total: `45`
- Coefficient rows total: `69`
- Operational prediction rows generated: `0`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 21 trains simple offline interpretable research models only for benchmark metrics. These outputs are not trading signals, recommendations, allocations, or operational decisions.

## Latest Phase 22 update

Updated at: 2026-07-04T20:06:10.466908+00:00

- Phase 22 gate: `PHASE22_MODEL_PERFORMANCE_TRIAGE_RESEARCH_GATE_READY_RESEARCH_ONLY`
- Model performance triage ready: `True`
- Research path forward: `VOLATILITY_FIRST_RESEARCH_PATH`
- Return model research gate: `BLOCK_RETURN_MODEL_ADVANCEMENT_RESEARCH_ONLY`
- Return holdout beat rate: `0.16666667`
- Abs-return holdout beat rate: `0.66666667`
- Volatility holdout beat rate: `0.83333333`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 22 is a research triage gate only. It does not create trading signals, recommendations, allocations, or operational decisions.

## Latest Phase 23 update

Updated at: 2026-07-04T20:14:19.575856+00:00

- Phase 23 gate: `PHASE23_VOLATILITY_FIRST_RESEARCH_BENCHMARK_READY_RESEARCH_ONLY`
- Volatility-first benchmark ready: `True`
- Phase 22 triage ready: `True`
- Holdout beats total: `1`
- Coins with best model improvement: `1`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 23 is volatility-first research benchmarking only. It creates no trading signals, recommendations, allocations, or operational decisions.
