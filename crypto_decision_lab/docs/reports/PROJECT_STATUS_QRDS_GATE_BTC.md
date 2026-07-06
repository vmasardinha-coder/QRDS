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

Updated at: 2026-07-04T20:19:11.420903+00:00

- Phase 23 gate: `PHASE23_VOLATILITY_FIRST_RESEARCH_BENCHMARK_READY_RESEARCH_ONLY`
- Volatility-first benchmark ready: `True`
- Phase 22 triage ready: `True`
- Holdout beats total: `1`
- Coins with best model improvement: `1`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 23 is volatility-first research benchmarking only. It creates no trading signals, recommendations, allocations, or operational decisions.

## Latest Phase 24 update

Updated at: 2026-07-04T20:39:56.025254+00:00

- Phase 24 gate: `PHASE24_VOLATILITY_RESIDUAL_DIAGNOSTICS_BASELINE_ROBUSTNESS_READY_RESEARCH_ONLY`
- Diagnostics ready: `True`
- Diagnostic path forward: `STRENGTHEN_VOLATILITY_BASELINES_AND_FEATURES_RESEARCH_ONLY`
- Complex model allowed by triage: `False`
- Holdout beats total: `1`
- Coins with best model improvement: `1`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 24 is diagnostics only and recommends no operational action. It blocks complex-model escalation when robustness is weak.

## Latest Phase 25 update

Updated at: 2026-07-04T20:58:30.057919+00:00

- Phase 25 gate: `PHASE25_VOLATILITY_FEATURE_BASELINE_STRENGTHENING_READY_RESEARCH_ONLY`
- Strengthening ready: `True`
- Metric rows total: `99`
- Holdout beats vs Phase 20: `4`
- Holdout beats vs Phase 23: `5`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 25 strengthens volatility baselines/features only. It creates no trading signals, recommendations, allocations, or operational decisions.

## Latest Phase 26 update

Updated at: 2026-07-04T21:23:36.530818+00:00

- Phase 26 gate: `PHASE26_REGIME_SEGMENTED_VOLATILITY_EDGE_AUDIT_READY_RESEARCH_ONLY`
- Regime edge audit ready: `True`
- Research edge candidates: `4`
- Operational edge validated: `False`
- Decision layer allowed: `False`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 26 audits potential edge by regime. Research candidates are not operational edge and do not authorize signals, recommendations, allocations, or decisions.

## Latest Phase 27 update

Updated at: 2026-07-04T21:29:59.624615+00:00

- Phase 27 gate: `PHASE27_EDGE_CANDIDATE_STABILITY_ANTI_OVERFIT_READY_RESEARCH_ONLY`
- Candidate stability ready: `True`
- Candidates tested: `4`
- Stable research candidates: `0`
- Operational edge validated: `False`
- Decision layer allowed: `False`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 27 tests anti-overfit stability of Phase 26 edge candidates. Stable candidates remain research-only and do not authorize decisions.

## Latest Phase 28 update

Updated at: 2026-07-04T21:38:04.658012+00:00

- Phase 28 gate: `PHASE28_REGIME_TAXONOMY_COMPRESSION_FAILURE_ANALYSIS_READY_RESEARCH_ONLY`
- Regime compression ready: `True`
- Failure rows: `4`
- Compression map rows: `4`
- Next research path: `RETEST_COMPRESSED_REGIME_EDGE_CANDIDATES_RESEARCH_ONLY`
- Decision layer allowed: `False`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 28 converts unstable fine-grained edge candidates into compressed-regime retest inputs. It validates no operational edge.

## Latest Phase 29 update

Updated at: 2026-07-04T23:02:39.676708+00:00

- Phase 29 gate: `PHASE29_COMPRESSED_REGIME_EDGE_RETEST_READY_RESEARCH_ONLY`
- Compressed retest ready: `True`
- Retests: `4`
- Stable compressed candidates: `0`
- Operational edge validated: `False`
- Decision layer allowed: `False`
- Next research path: `REBUILD_FEATURES_AND_BASELINES_NO_EDGE_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 29 retests compressed-regime candidates. Stable compressed candidates remain research-only and do not authorize decisions.

## Latest Phase 30 update

Updated at: 2026-07-05T00:28:22.730872+00:00

- Phase 30 gate: `PHASE30_NO_EDGE_CHECKPOINT_RISK_REGIME_DASHBOARD_READINESS_READY_RESEARCH_ONLY`
- No-edge checkpoint ready: `True`
- Edge validated: `False`
- Risk/regime dashboard research ready: `True`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Next research path: `BUILD_RISK_REGIME_RESEARCH_DASHBOARD_MVP_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 30 records no validated edge from the current volatility/regime path and opens the research-only risk/regime dashboard path. No shadow or operational decision is allowed.

## Latest Phase 31 update

Updated at: 2026-07-05T00:48:20.566059+00:00

- Phase 31 gate: `PHASE31_RISK_REGIME_RESEARCH_DASHBOARD_MVP_READY_RESEARCH_ONLY`
- Dashboard MVP ready: `True`
- Dashboard cards: `6`
- Edge validated: `False`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Next research path: `HARDEN_RISK_REGIME_DASHBOARD_AND_ADD_NAVIGATION_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 31 delivers the first research-only risk/regime dashboard MVP. It remains non-decision, non-signal, and non-operational.

## Latest Phase 32 update

Updated at: 2026-07-05T01:01:00.919524+00:00

- Phase 32 gate: `PHASE32_RISK_REGIME_DASHBOARD_NAVIGATION_HARDENING_READY_RESEARCH_ONLY`
- Navigation hardening ready: `True`
- Navigation pages: `7`
- Edge validated: `False`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Next research path: `ADD_FRESHNESS_AND_DRILLDOWN_STATUS_PANELS_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 32 hardens the research-only dashboard into a navigable portal with module pages and manifests. It remains non-decision, non-signal, and non-operational.

## Latest Phase 33 update

Updated at: 2026-07-05T01:09:42.775111+00:00

- Phase 33 gate: `PHASE33_FRESHNESS_DRILLDOWN_STATUS_PANELS_READY_RESEARCH_ONLY`
- Freshness/drilldown panels ready: `True`
- Freshness rows: `12`
- Page drilldown rows: `7`
- Module drilldown rows: `5`
- Edge validated: `False`
- Decision layer allowed: `False`
- Next research path: `ADD_LATEST_OBSERVATION_AND_REGIME_SNAPSHOT_PANELS_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 33 adds freshness and drilldown status panels to the research-only dashboard. It remains non-decision, non-signal, and non-operational.

## Latest Phase 34 update

Updated at: 2026-07-05T01:19:43.257435+00:00

- Phase 34 gate: `PHASE34_LATEST_OBSERVATION_REGIME_SNAPSHOT_READY_RESEARCH_ONLY`
- Latest/regime snapshot ready: `True`
- Latest observation rows: `3`
- Regime snapshot rows: `3`
- Source status rows: `3`
- Edge validated: `False`
- Decision layer allowed: `False`
- Next research path: `ADD_TIME_SERIES_SPARKLINE_AND_RECENT_HISTORY_PANELS_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 34 adds latest observation and regime snapshot panels to the research-only dashboard. It remains non-decision, non-signal, and non-operational.

## Latest Phase 35 update

Updated at: 2026-07-05T01:35:19.266010+00:00

- Phase 35 gate: `PHASE35_RECENT_HISTORY_SPARKLINE_PANELS_READY_RESEARCH_ONLY`
- Recent history/sparkline panels ready: `True`
- Recent history rows: `288`
- Sparkline rows: `9`
- Transition summary rows: `3`
- Edge validated: `False`
- Decision layer allowed: `False`
- Next research path: `ADD_DASHBOARD_EXPORT_AND_REVIEW_BUNDLE_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 35 adds recent-history and sparkline panels to the research-only dashboard. It remains non-decision, non-signal, and non-operational.

## Latest Phase 36 update

Updated at: 2026-07-05T01:48:22.971293+00:00

- Phase 36 gate: `PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY`
- Unified portal ready: `True`
- Navigation pages: `11`
- Required sections present: `11`
- Edge validated: `False`
- Decision layer allowed: `False`
- Next research path: `ADD_EXPORT_REVIEW_BUNDLE_AND_SINGLE_PORTAL_INDEX_RESEARCH_ONLY`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Canonical writes: `0`

Phase 36 consolidates the Phase 31–35 mini-portals into one unified research-only portal shell. It remains non-decision, non-signal, and non-operational.

<!-- PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX:START -->

## Phase 37 — Export Review Bundle + Single Portal Index

Gate: `PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY`

Generated at UTC: `2026-07-05T01:57:38+00:00`

Research-only safety state:

- app_mode: `INTERACTIVE_RESEARCH_ONLY`
- policy_lock: `ACTIVE`
- operational_status: `BLOCKED_RESEARCH_ONLY`
- edge_validated: `False`
- edge_operationally_validated: `False`
- shadow_decision_allowed: `False`
- decision_layer_allowed: `False`
- trading_signal_generated: `False`
- recommendation_generated: `False`
- allocation_generated: `False`
- operational_decision_allowed: `False`
- safe_apply_allowed: `False`
- promotion_allowed: `False`
- canonical_data_writes: `0`

Review bundle:

- review_bundle_ready: `True`
- required_phase36_page_count: `11`
- present_phase36_page_count: `11`
- source_file_count: `20`
- checksum_file_count: `20`
- zip_created: `True`
- output_dir: `/workspaces/QRDS/artifacts/phase37_export_review_bundle_single_portal_index`

Interpretation:

Phase 37 only packages and indexes the Phase 36 unified research portal for review. It does not validate edge, does not create a shadow decision layer, and does not permit operational use.

<!-- PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX:END -->

<!-- PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_START -->

## Phase 38 — Modern Research Portal Layout / UX Polish

- Gate: `PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_READY_RESEARCH_ONLY`
- Modern portal ready: `True`
- Phase 37 ready: `True`
- Required sections present: `11 / 11`
- Source files copied: `0`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Edge validated: `False`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Trading signal generated: `False`
- Recommendation generated: `False`
- Allocation generated: `False`
- Canonical data writes: `0`
- Generated at UTC: `2026-07-05T02:04:40+00:00`

Interpretação: a Phase 38 moderniza layout e UX do portal de pesquisa. Não cria interpretação operacional, recomendação, sinal, alocação, ordem, safe-apply ou promoção canônica.

<!-- PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_END -->

<!-- PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE -->

## Phase 39 — Interpretation Readiness + Information Architecture

- Gate: `PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE_READY_RESEARCH_ONLY`
- Generated at: `2026-07-06T15:59:01.608188+00:00`
- Phase 38 ready: `True`
- Interpretation pages: `8`
- Metric dimensions: `7`
- Candidate history: 4 research candidates from Phase 26, 0 stable after Phases 27–29.
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Edge validated: `False`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Trading signal generated: `False`
- Recommendation generated: `False`
- Allocation generated: `False`
- Canonical data writes: `0`

Phase 39 adds a non-operational reading architecture over the modern research portal. It improves comprehension, glossary, metric mapping, evidence boundaries, and candidate-failure history. It does not create a signal, recommendation, allocation, shadow decision, safe-apply, canonical promotion, or operational decision.


## Phase 43 — Candidate Lifecycle Registry

Gate: `PHASE43_CANDIDATE_LIFECYCLE_REGISTRY_READY_RESEARCH_ONLY`  
Operational: `BLOCKED_RESEARCH_ONLY`  
Edge validated: `False`  
canonical_data_writes: `0`  

Scope: formal research-only candidate lifecycle registry. Phase 26 historical candidates remain recorded as 4 failed research candidates; stable candidates remain 0; shadow-eligible candidates remain 0; operational candidates remain 0. No trading signal, recommendation, allocation, shadow decision, safe-apply, promotion, canonical write, or operational decision was created.
