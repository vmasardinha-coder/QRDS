# BTSE 2.0 external systems inventory — 2026-09-21

## Scope

This inventory reconstructs the original 15-system BTSE 2.0 radar and separates later-added execution/backtest auditors. The decision rule is practical: retain only systems that can plausibly contribute an economically new family, a measurable component, or an independent auditor. UI/wrapper/media/productivity projects are not advanced merely because they are technically interesting.

## Original 15-system radar

| System | Relevant to trading research? | Tested? | Status | Role | Family / idea extracted | Migrated? | Next step |
|---|---|---|---|---|---|---|---|
| TradingAgents | Yes | Yes | HOLD_FOR_ECONOMIC_BENCHMARK | COMPONENT / possible ensemble research | multiagent debate/divergence hypothesis not yet economically proven | No | Revisit only with a preregistered economic benchmark |
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

## Later-added relevant auditors / engines

These are not part of the reconstructed original 15, but were sensibly added because they can independently challenge research/execution semantics.

| System | Relevant? | Tested? | Status | Role | Family / idea extracted | Migrated? | Next step |
|---|---|---|---|---|---|---|---|
| QuantConnect LEAN | Yes | Yes | CONCLUDED / RETAIN_AS_EXECUTION_AND_BACKTEST_AUDITOR | AUDITOR | capacity / slippage stress via VolumeShareSlippageModel; default saturation caveat | No | Use as independent execution/capacity auditor, not canonical model |
| Backtrader | Yes | Yes | CONCLUDED / AUDITOR | AUDITOR | execution_timing_semantics_audit / engine parity | No; finding overlaps `AUDIT-XEXEC-01` | Use as second-engine parity auditor when useful |

## Answer to the inventory question

Among the **economically relevant systems in the original 15**, the active research set has already been covered: TradingAgents, Fincept Terminal, NautilusTrader, Freqtrade, AI Hedge Fund, CCXT, Hummingbot, Jesse, and FinRL/FinRL-X.

The remaining original-radar projects are primarily agent/UI/media/productivity infrastructure and do not currently justify BTSE scientific throughput because they do not expose a concrete new alpha family, market-data signal, microstructure mechanism, factor, regime detector, derivatives capability, execution model, or measurable risk overlay.

Therefore there is **no missing high-priority original-radar trading system that should be tested merely to complete the count of 15**.

The correct next-stage metric remains:

`new economic families -> tested families -> survivors -> incremental gain over QRDS`

not number of external platforms executed.

## Current external-system scientific map

### Migrated into Factory
- `H-XREGIME-01 / cross_asset_regime_gate` from Freqtrade — candidate hypothesis, independently revalidated by Factory.
- `AUDIT-XEXEC-01 / execution_realism_stress` from NautilusTrader — methodology/audit gate only.
- `AUDIT-XAVAIL-01 / signal_availability_semantics` from AI Hedge Fund — integrity guard only.

### Retained externally
- TradingAgents — economic benchmark pending.
- Freqtrade — recurring family source and auditor.
- Jesse — periodic hypothesis source.
- Hummingbot — microstructure / market-making family source.
- FinRL — RL sandbox, with frozen tested formulation rejected.
- CCXT — transport/source probe.
- Fincept — reference only.
- LEAN — execution/capacity auditor.
- Backtrader — execution semantics / engine-parity auditor.

## Recommended next direction

Do not continue by installing the remaining low-relevance original projects. The next external research pass should target missing **capability classes**, not missing brand names, with priority on:

1. order-book / microstructure and cross-venue lead-lag;
2. derivatives / basis / funding / volatility surface;
3. anomaly and change-point detection;
4. nonlinear factor discovery;
5. alternative-data signals with provable PIT semantics;
6. online learning / adaptive allocation with strict OOS discipline.

Any new external system should be admitted only if it has a credible path to one of those classes and can produce a tangible standalone artifact before integration.
