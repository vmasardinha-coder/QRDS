# TradingAgents economic benchmark adjudication — 2026-09-21

## Scope

This adjudication closes the outstanding `HOLD_FOR_ECONOMIC_BENCHMARK` question for TradingAgents without fabricating a provider-backed run that the current BTSE research environment cannot reproduce.

This is external BTSE research only. It does not modify Factory logic, V2A/PIT collectors, source registries, canonical runtime, engine feeds, orders, or capital.

## Prior standalone state

TradingAgents had already been installed/tested standalone and its architecture was verified. The unresolved question was economic: whether the multi-agent debate / disagreement / risk-veto structure adds measurable decision quality beyond a simpler baseline.

## Current upstream re-check

Pinned upstream state inspected for this adjudication:

- repository: `TauricResearch/TradingAgents`
- upstream commit: `2d17df8da1536c121e4d7395ac5a5dcec9e96d6f`
- release line: `v0.5.0`

The current upstream materially improves the scientific surface versus the earlier review:

- point-in-time integrity fixes across dated data paths;
- backtesting over ticker/date grids;
- regional benchmark selection for alpha calculations;
- portfolio-aware runtime state;
- support for crypto tickers such as `BTC-USD` and `ETH-USD`;
- multiple hosted LLM providers plus local Ollama / OpenAI-compatible endpoints.

These changes improve benchmarkability, but they do not eliminate the provider dependency of the actual multi-agent decision path.

## What the built-in backtest does and does not prove

The upstream backtest aggregates many single-shot decisions and scores realized return / alpha against a benchmark over a configured holding period.

The upstream tests explicitly state that the backtest:

- evaluates decision quality;
- does **not** simulate a portfolio;
- has no execution model;
- has no fees;
- has no equity curve.

Therefore even a successful TradingAgents built-in backtest would be a decision-quality benchmark, not a full economic execution benchmark comparable to a QRDS equity curve without an additional adapter.

## Provider / reproducibility boundary

Generating the actual TradingAgents decisions requires one of:

- a hosted LLM provider credential (`OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, etc.); or
- a running local/remote Ollama endpoint; or
- a running OpenAI-compatible local endpoint such as vLLM / LM Studio / llama.cpp.

The connected BTSE research CI used for this adjudication does not expose an authorized provider credential or a preregistered local inference endpoint for TradingAgents.

Using a stub, mocked model, hand-authored decisions, or a different ad-hoc local model would test plumbing but would **not** answer the frozen economic question about the real multi-agent system. That substitution is therefore rejected.

## Scientific disposition

`TradingAgents = HOLD / PROVIDER_REPRODUCIBILITY_BLOCKED_FOR_ECONOMIC_BENCHMARK`

This is not a rejection of the framework and not a pass of the economic hypothesis.

What is established:

- standalone framework capability exists;
- the current upstream has materially better PIT/backtest mechanics than the earlier version;
- it can produce tangible analyst/researcher/trader/risk outputs when a real provider is configured;
- its built-in backtest can score decision quality over ticker/date grids.

What is **not** established:

- incremental alpha versus QRDS;
- superiority of multi-agent debate versus a simpler LLM baseline;
- benefit of disagreement as an uncertainty signal;
- benefit of risk-veto as an abstention gate;
- execution-aware PnL after costs;
- an equity-curve advantage.

## Exact condition to reopen

Reopen only when one of these is available and frozen before observing outcomes:

1. an authorized hosted LLM provider credential usable by CI; or
2. a version-pinned local OpenAI-compatible/Ollama endpoint with model hash/revision, deterministic-enough decoding settings, and reproducible availability.

Then preregister a paired benchmark using the same ticker/date cells and data path:

- arm A: full TradingAgents multi-agent pipeline;
- arm B: simpler single-agent/control decision path using the same backbone model and data;
- same holding period and benchmark;
- fixed sampling/temperature settings where supported;
- repeated samples if provider nondeterminism requires it;
- decision-quality metrics first;
- only after that, an external execution/cost adapter for equity-curve comparison.

No winner parameters, debate rounds, prompts, providers, tickers, dates, or thresholds may be selected after observing the paired result.

## Safety / integration boundary

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`

No Factory integration follows from this adjudication.
