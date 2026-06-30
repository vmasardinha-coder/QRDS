# QRDS / QOS — Context Pack 7G

This is the compact official project context after Sprint 7G.

Use this as the lightweight state if the chat becomes heavy.

---

## Project identity

QRDS / QOS is a **Crypto Decision Lab**.

It is a research framework for studying:

```text
data quality
features
regimes
targets
walk-forward validation
baseline models
benchmark models
hypothetical replay
cost/slippage assumptions
edge reports
research report packs
```

It is **not** a trading bot.

---

## Official mode

`INTERACTIVE_RESEARCH_ONLY`

---

## Absolute safety boundaries

The project still forbids:

```text
API keys
real accounts
authenticated exchange access
orders
real capital
leverage
operational decisions
executable trading signals
recommendations to trade
```

Every artifact must remain research-only.

---

## Current approved chain

```text
Safety
↓
DQL
↓
Feature Engineering
↓
Regime Diagnostics
↓
Target Labels
↓
Integrated Research Dataset
↓
Dataset Export
↓
Research Run Manifest
↓
Research Run Bundle
↓
Research Run Registry
↓
Pipeline Orchestrator
↓
Offline CLI
↓
Research Fixtures
↓
Public Data Adapter Contract
↓
OKX Public Research Adapter
↓
Public Data Cache Layer
↓
Walk-forward Splitter
↓
Baseline Model Layer
↓
Backtest Skeleton
↓
Edge Report v1
↓
Integration Health / Contract Freeze
↓
Edge Report Artifact Export
↓
Full Research CLI Runner
↓
Root Runner Wrapper
↓
Multi-Asset Fixture Replay
↓
Cost & Slippage Research Model
↓
Benchmark Model Comparison
↓
Research Report Pack v1
```

---

## Last approved sprint

`7G — Research Report Pack v1`

---

## Current user-facing root commands

From repository root:

```bash
bash qrds_full_research.sh \
  --output-dir artifacts/full_research \
  --run-id full-research-run \
  --report-id edge-report
```

```bash
bash qrds_report_pack.sh \
  --full-research-dir artifacts/full_research \
  --output-dir artifacts/report_pack
```

---

## Current artifact outputs

Full research output:

```text
full_research_summary.json
integration_health_report.json
contract_freeze_registry.json
edge_console_summary.json
edge_exports/<report-id>/edge_report.json
edge_exports/<report-id>/edge_summary.json
edge_exports/<report-id>/edge_export_index.json
```

Report pack output:

```text
research_report.md
research_report_pack.json
artifact_map.json
research_report_pack_index.json
```

---

## Current fixture coverage

Offline OKX-shaped public fixtures:

```text
BTC-USDT
ETH-USDT
SOL-USDT
```

Fixtures live in:

```text
data/fixtures/okx_public/
```

Do not put OKX-shaped fixtures inside:

```text
data/fixtures/research/
```

because that directory has a different schema contract.

---

## Key implementation map

```text
src/crypto_decision_lab/contracts/research.py
src/crypto_decision_lab/data/public_adapter.py
src/crypto_decision_lab/data/okx_public.py
src/crypto_decision_lab/data/cache.py
src/crypto_decision_lab/validation/walk_forward.py
src/crypto_decision_lab/models/baseline.py
src/crypto_decision_lab/models/benchmarks.py
src/crypto_decision_lab/backtests/skeleton.py
src/crypto_decision_lab/costs/slippage.py
src/crypto_decision_lab/reports/edge.py
src/crypto_decision_lab/reports/export.py
src/crypto_decision_lab/reports/pack.py
src/crypto_decision_lab/cli/full_research.py
src/crypto_decision_lab/cli/report_pack.py
```

Root wrappers:

```text
qrds_full_research.sh
qrds_report_pack.sh
```

---

## Important resolved issues

1. OKX fixture schema separation:
   - OKX-shaped payload fixtures belong in `data/fixtures/okx_public/`.
   - Generic research fixtures belong in `data/fixtures/research/`.

2. Cache key determinism:
   - cache key ignores volatile `generated_at`.

3. Full research root usage:
   - root wrapper added so the user can run from `/workspaces/QRDS`.

4. Fixture safety stamp:
   - OKX fixtures must include `app_mode = INTERACTIVE_RESEARCH_ONLY`.

---

## Current maturity

The project can now generate a complete offline research report pack.

Still missing before any realistic decision research:

```text
realistic cost/slippage calibration
larger data fixtures or public no-auth ingestion
multi-asset aggregation reports
stress tests across more regimes
model validation beyond deterministic benchmarks
clear separation between research score and operational decision
```

---

## Recommended next block

Start Block 8 with:

```text
8A — Multi-Asset Report Aggregator
```

Purpose:
- aggregate several full research/report-pack outputs
- compare edge status across symbols
- compare benchmark/cost/edge summaries
- produce one portfolio-level research dashboard artifact
- still no allocation, no signal and no recommendation

Possible next sequence:

```text
8A — Multi-Asset Report Aggregator
8B — Scenario Stress Pack
8C — Data Coverage Expansion
8D — Public No-Auth Fetch Adapter Planning
8E — Research Scorecard v1
```
