# BTSE 2.0 external systems inventory — 2026-09-21

## Scope

This inventory reconstructs the original 15-system BTSE 2.0 radar and separates later-added execution/backtest auditors and capability probes. The decision rule is practical: retain only systems that can plausibly contribute an economically new family, a measurable component, or an independent auditor. UI/wrapper/media/productivity projects are not advanced merely because they are technically interesting.

## Original 15-system radar

| System | Relevant to trading research? | Tested? | Status | Role | Family / idea extracted | Migrated? | Next step |
|---|---|---|---|---|---|---|---|
| TradingAgents | Yes | Yes | HOLD / PROVIDER_REPRODUCIBILITY_BLOCKED_FOR_ECONOMIC_BENCHMARK | COMPONENT / possible ensemble research | multiagent debate/divergence, risk-veto / abstention ideas not yet economically proven | No | Reopen only with authorized reproducible LLM provider/local endpoint and paired preregistered benchmark |
| Fincept Terminal | Yes | Yes | CONCLUDED / REFERENCE_ONLY | FACTOR REFERENCE | factor evaluation semantics; no superior new family found | No | Periodic reference only |
| NautilusTrader | Yes | Yes | CONCLUDED / AUDITOR | EXECUTION AUDITOR | execution_realism_stress | Yes, methodology only as `AUDIT-XEXEC-01` | Use on compatible survivor execution audits |
| Freqtrade | Yes | Yes | CONCLUDED / RETAIN_AS_RADAR_AND_AUDITOR | FAMILY SOURCE / AUDITOR | `cross_asset_regime_gate`; other strategy-family seeds | Yes: `H-XREGIME-01`; separate industrial seeds also evaluated | Periodic family mining, not platform migration |
| AI Hedge Fund | Yes | Yes | CONCLUDED / COMPONENT | INTEGRITY COMPONENT | `abstain/unavailable != neutral` | Yes as `AUDIT-XAVAIL-01` | Reuse only as availability-semantics guard |
| CCXT | Yes, infrastructure only | Yes | COMPONENT / SOURCE_PROBE / TRANSPORT | DATA/TRANSPORT COMPONENT | multi-exchange normalization / source access | No | Use as external research transport when useful |
| Hummingbot | Yes | Yes | CONCLUDED | COMPONENT / FAMILY SOURCE | inventory skew as risk control; market-making/microstructure source | No alpha migration | Revisit for genuinely new microstructure families only |
| Jesse | Yes | Yes | CONCLUDED / HYPOTHESIS_SOURCE | FAMILY SOURCE | Dual Thrust | No; `HOLD_RESEARCH_NOT_MIGRATED` | Periodic family mining only |
| FinRL / FinRL-X | Yes | Yes | CONCLUDED / RETAIN_AS_RL_RESEARCH_SANDBOX | RL SANDBOX | policy-gradient portfolio allocation tested and rejected in frozen configuration | No | New RL work must be a fresh preregistered hypothesis |
| LibreChat | No material economic edge identified | No BTSE economic test needed | REJECT_AS_BTSE_RESEARCH_PRIORITY | UI / orchestration wrapper | none | No | Do not spend research budget unless a concrete trading capability emerges |
| ElizaOS | Low / indirect | No BTSE economic test needed now | HOLD / LOW_PRIORITY | agent framework | none yet | No | Revisit only if tied to a measurable trading family or auditor |
| HyperFrames | No for BTSE trading research | Explored outside BTSE | REJECT_AS_BTSE_RESEARCH_PRIORITY | visual/video generation | none | No | Keep outside trading research |
| MoneyPrinterTurbo | No for BTSE trading research | Explored outside BTSE | REJECT_AS_BTSE_RESEARCH_PRIORITY | media automation | none | No | Keep outside trading research |
| VoxCPM / VoxCPM2 | No for BTSE trading research | Explored outside BTSE | REJECT_AS_BTSE_RESEARCH_PRIORITY | speech/audio generation | none | No | Keep outside trading research |
| Agentic Inbox | No material economic edge identified | No BTSE economic test needed | REJECT_AS_BTSE_RESEARCH_PRIORITY | productivity / inbox automation | none | No | Keep outside trading research |

## Later-added relevant auditors / capability probes

| System / capability | Status | Tangible standalone result | Factory / BTSE disposition |
|---|---|---|---|
| QuantConnect LEAN | CONCLUDED / RETAIN_AS_EXECUTION_AND_BACKTEST_AUDITOR | independent execution/capacity stress | auditor only |
| Backtrader | CONCLUDED / AUDITOR | engine/order-lifecycle semantic divergence quantified | second-engine parity auditor |
| Qlib | CONCLUDED / RETAIN_AS_NONLINEAR_FACTOR_RESEARCH_SANDBOX | Alpha158/LightGBM capability benchmark passed; historical PIT authority insufficient for QRDS integration | sandbox only |
| River | ONLINE_ML / DRIFT_RESEARCH_SANDBOX | frozen ADWIN reset hypothesis produced zero drifts and no improvement | tested formulation rejected |
| BOCPD | CONCLUDED / frozen formulation rejected | causal change-point overlay failed enrichment/economic gates | no migration |
| Cryptofeed | COMPONENT / CROSS-VENUE CAPTURE | simultaneous Binance/OKX L2 capture worked; frozen 250ms Binance→OKX lead-lag hypothesis rejected | capture component only |
| QuantLib + Deribit | RETAIN_AS_OPTIONS_PRICING_AUDITOR | 957 BTC options across 11 expiries reconstructed; 100% within frozen mark tolerance | options/IV auditor only |
| Coin Metrics Community API | SOURCE_RETAINED_AS_RESEARCH_COMPONENT | 7d active-address gate cut DD but retained only 59.77% of buy-and-hold terminal equity | frozen feature rejected; source retained |
| FinBERT | COMPONENT / HOLD_FOR_TEMPORAL_CRYPTO_NEWS_DATA | 970 Financial PhraseBank test samples, 86.49% accuracy, 85.61% macro-F1 | NLP capability passed; no crypto-news alpha claim |

## Current scientific map

### Migrated into Factory
- `H-XREGIME-01 / cross_asset_regime_gate` from Freqtrade — candidate hypothesis, independently revalidated by Factory.
- `AUDIT-XEXEC-01 / execution_realism_stress` from NautilusTrader — methodology/audit gate only.
- `AUDIT-XAVAIL-01 / signal_availability_semantics` from AI Hedge Fund — integrity guard only.

### Retained externally
- TradingAgents — architecture verified; economic paired benchmark blocked until a reproducible authorized LLM provider/local endpoint exists.
- Freqtrade — recurring family source and auditor.
- Jesse — periodic hypothesis source.
- Hummingbot — microstructure / market-making family source.
- FinRL — RL sandbox, with frozen tested formulation rejected.
- CCXT — transport/source probe.
- Fincept — reference only.
- LEAN / Backtrader — execution auditors.
- Qlib — nonlinear-factor sandbox.
- Cryptofeed — cross-venue capture component.
- QuantLib — options/volatility auditor.
- Coin Metrics — on-chain research source.
- FinBERT — sentiment classifier awaiting admissible timestamped crypto-news history.

## Capability-class coverage

The six capability gaps identified in the prior inventory have now all received at least one frozen external test:

1. order-book / cross-venue microstructure — Cryptofeed tested; capture passed, frozen lead-lag rejected;
2. derivatives / volatility surface — QuantLib + Deribit passed as pricing auditor;
3. anomaly / change-point detection — BOCPD frozen formulation rejected;
4. nonlinear factor discovery — Qlib capability passed, integration blocked by historical PIT authority;
5. alternative data — Coin Metrics feature rejected; FinBERT NLP capability passed but temporal crypto-news integration is blocked;
6. online learning / adaptive allocation — River frozen ADWIN formulation rejected.

Therefore the next external research should **not** be driven by completing brand counts or retuning failed frozen hypotheses. New work should enter only when it supplies one of:

- a genuinely new economic family not already represented;
- admissible PIT data that unlocks a currently blocked capability;
- a reproducible provider needed to resolve an existing HOLD;
- an independent audit that materially challenges a surviving QRDS result.

The practical metric remains:

`new economic families -> tested families -> survivors -> incremental gain over QRDS`

not number of external platforms executed.
