# Architecture — crypto_decision_lab

## Overview

`crypto_decision_lab` is the consolidated QRDS/QOS research system. It runs
exclusively in `INTERACTIVE_RESEARCH_ONLY` mode and produces research
artifacts (reports, datasets, dashboards) without any operational trading
capability.

## Layered design

```
config/      → mode + settings, no external calls
safety/      → gates, policies, assertions (imported by everything else)
domain/      → core models/schemas, no business logic
exchanges/   → public/sim connectors only, role-gated
data/        → candle normalization, fixtures
dql/         → data quality validation and reporting
features/    → feature engineering + quality
regimes/     → market regime diagnostics
targets/     → target label engineering + quality
research/    → integrated dataset, temporal validation, baseline model,
               decision readiness
backtest/    → research-only backtest engine
risk/        → research-only risk engine
paper/       → offline paper trading + validation
pipelines/   → orchestrates the above into end-to-end runs
dashboard/   → HTML + Streamlit presentation layers
export/      → JSON/TXT artifact writers
```

## Dependency direction

`safety/` and `config/` have zero internal dependencies — every other module
may depend on them, but they depend on nothing else in the package. This
prevents safety gates from ever being bypassed by a circular import or a
partially-initialized module.

```
config, safety  (leaf — no internal deps)
   ↑
domain
   ↑
data, exchanges
   ↑
dql, features, regimes, targets
   ↑
research, backtest, risk, paper
   ↑
pipelines
   ↑
dashboard, export
```

## Pipelines

- `pipelines/offline_research.py` — runs the full offline research chain
  (DQL → features → regimes → targets → research reports) using Binance
  simulation data only.
- `pipelines/public_live_dql.py` — runs DQL validation against OKX live
  public data plus Binance simulation as benchmark.
- `pipelines/public_live_research.py` — full research pipeline integration
  using OKX live + Binance simulation.

Every pipeline entry point calls `safety.assertions.assert_pipeline_context_safe()`
before returning any result.
