# TradingAgents isolated discovery — 2026-09-21

RESEARCH_ONLY=true  
SHADOW_ONLY=true

Upstream: `TauricResearch/TradingAgents`  
Pinned SHA: `2d17df8da1536c121e4d7395ac5a5dcec9e96d6f`  
Pinned package version: `0.5.0`

## Research question
Determine whether TradingAgents contributes a reproducible, migratable research concept to GATE BTC 2.0 beyond what Freqtrade and NautilusTrader already supplied.

## Boundaries
- No upstream trading-performance claim is imported as evidence.
- No external LLM output is treated as deterministic ground truth.
- No Factory family is modified in this research branch.
- No capital activation or live trading.
- API-dependent multi-agent propagation must not be claimed as tested unless an actual provider run occurs.

## Candidate contributions
1. Role-separated evidence channels (technical/news/fundamental/sentiment).
2. Bull-versus-bear adversarial debate as an uncertainty/disagreement signal.
3. Aggressive/conservative/neutral risk debate as an abstention or confidence-control signal.
4. Point-in-time safe decision memory / historical decision settlement.
5. Structured decision artifacts that preserve analyst/research/trader/portfolio hand-offs.

## Falsification criteria
- If the framework cannot be installed/tested at the pinned SHA, standalone fails.
- If point-in-time safeguards are only claims and not covered by code/tests, PIT contribution is unproven.
- If debate disagreement cannot be reduced to a deterministic auditable feature without importing LLM prose semantics, it is not ready to migrate.
- If economic usefulness requires provider-specific LLM behavior and cannot be independently benchmarked, retain as a research architecture candidate rather than a Factory hypothesis.

## Known backtest boundary
The upstream unit-test contract states that TradingAgents backtesting evaluates many single-shot decisions over ticker/date grids and scores decision quality; it does not simulate a portfolio, execution, fees, or an equity curve. Therefore TradingAgents is not an execution-audit replacement for Freqtrade/NautilusTrader.
