# TradingAgents closeout — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

Upstream: `TauricResearch/TradingAgents`  
Pinned SHA: `2d17df8da1536c121e4d7395ac5a5dcec9e96d6f`  
Version: `0.5.0`

## What was proven
- The pinned package installs successfully under Python 3.12.
- 143 selected upstream unit tests passed covering backtest grid behavior, point-in-time memory, tool date enforcement, fundamentals lookahead, structured agents, signal parsing and portfolio context.
- The framework maintains independent bull/bear debate channels and aggressive/conservative/neutral risk channels.
- Research Manager, Trader and Portfolio Manager decisions are structured and can be mapped to a deterministic cross-handoff disagreement audit.
- A frozen structural POC correctly distinguishes aligned bullish/bearish handoffs from an explicit research-to-portfolio risk veto without invoking an LLM provider.

## What was not proven
- No API-dependent multi-agent historical propagation was run.
- No economic value of debate, disagreement, consensus, risk veto or LLM reasoning was demonstrated.
- No alpha improvement versus a monolithic analyst, a single-agent baseline, or the current QRDS/Factory was demonstrated.
- TradingAgents' own backtest is not an execution simulator: it evaluates single-shot decisions across ticker/date grids and does not include portfolio simulation, fees, execution or an equity curve.

## Novelty assessment
Point-in-time memory and date enforcement are sound and useful, but they are not sufficiently novel to justify a new Factory family by themselves because GATE BTC already treats PIT/leakage controls as mandatory infrastructure.

Role-separated debate/disagreement is structurally auditable and potentially interesting, but predictive/economic usefulness remains unproven. Migrating it now as an official Factory alpha family would import an architectural intuition rather than a validated hypothesis.

## Disposition
**TRADINGAGENTS: STANDALONE VERIFIED / NO FACTORY MIGRATION YET / HOLD FOR ECONOMIC BENCHMARK.**

What migrates now: **nothing**.

What remains a candidate for a future bounded test:
- `multi_agent_disagreement_as_uncertainty`
- `risk_veto_as_abstention_gate`
- `role_separated_evidence_consensus`

Re-open only when an actual provider-backed point-in-time historical grid can compare the multi-agent architecture against a frozen single-agent/monolithic baseline on the same data, dates, model/provider/temperature budget and scoring rule. Any winner must then pass independent QRDS validation before Factory intake.
