# QRDS / QOS — Context Pack Phase 19

This is the compact project context after Sprint 6S / Phase 19.

Use this as the official lightweight context if the chat becomes too heavy.

---

## Project identity

QRDS / QOS is a **Crypto Decision Lab**.

It is currently a research framework for studying market data quality, features,
regimes, targets, datasets, walk-forward validation, baseline modeling,
hypothetical replay and edge reporting.

It is **not** a trading bot.

---

## Official mode

`INTERACTIVE_RESEARCH_ONLY`

---

## Absolute safety boundaries

- No API key.
- No real account.
- No authenticated exchange access.
- No orders.
- No real capital.
- No leverage.
- No operational decision.
- No executable trading signal.
- No recommendation to trade.

Every output that looks analytical must remain research-only.

---

## Current approved pipeline

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
```

---

## Last approved phase

`6S / Phase 19 — Edge Report v1`

Edge Report v1 produces research-only status labels:

- `NO_EVIDENCE`
- `WEAK_EVIDENCE`
- `PROMISING_RESEARCH_ONLY`
- `INCONCLUSIVE`

These are not trading recommendations.

---

## Current data path

```text
OKX-shaped offline fixture
↓
OKX public adapter
↓
Public candle batch
↓
Public data cache
↓
Normalized QRDS candles
↓
Research pipeline
↓
Dataset JSONL/CSV
↓
Walk-forward splits
↓
Baseline model
↓
Hypothetical backtest skeleton
↓
Edge Report v1
```

---

## Current implementation map

Important modules:

```text
src/crypto_decision_lab/safety/
src/crypto_decision_lab/features/
src/crypto_decision_lab/regimes/
src/crypto_decision_lab/targets/
src/crypto_decision_lab/datasets/
src/crypto_decision_lab/exports/
src/crypto_decision_lab/runs/
src/crypto_decision_lab/pipelines/
src/crypto_decision_lab/cli/
src/crypto_decision_lab/fixtures/
src/crypto_decision_lab/data/
src/crypto_decision_lab/validation/
src/crypto_decision_lab/models/
src/crypto_decision_lab/backtests/
src/crypto_decision_lab/reports/
```

Key files added in the latest block:

```text
src/crypto_decision_lab/data/public_adapter.py
src/crypto_decision_lab/data/okx_public.py
src/crypto_decision_lab/data/cache.py
src/crypto_decision_lab/validation/walk_forward.py
src/crypto_decision_lab/models/baseline.py
src/crypto_decision_lab/backtests/skeleton.py
src/crypto_decision_lab/reports/edge.py
```

---

## Fixture folders

```text
data/fixtures/research/
```

Generic research candle fixtures:
- bull
- neutral
- stress
- crash

```text
data/fixtures/okx_public/
```

OKX-shaped public payload fixtures.

Keep these separated. Do not put OKX payload fixtures inside
`data/fixtures/research/`, because the generic fixture catalog expects schema:

`qrds.research_candle_fixture.v1`

OKX payload fixtures use:

`qrds.okx_public_payload_fixture.v1`

---

## Recent issue resolved

The cache key initially used the whole batch hash including `generated_at`,
which made identical candle content produce different cache keys.

Resolution:
- cache key now uses stable public batch content hash
- volatile `generated_at` is excluded

---

## Operating rhythm

For large code work:
- Assistant creates downloadable `.sh`.
- User runs it in Codespaces.
- If success, user says `aprovado`.
- If error, user pastes only the error.
- Assistant sends a targeted hotfix `.sh`.

Avoid asking for confirmation after every sprint unless a real decision is needed.

---

## User preference

The user prefers:
- Portuguese
- direct/pragmatic explanation
- downloadable shell scripts
- visual pipeline summaries
- periodic context packs/checkpoints
- no excessive terminal/code blocks in chat

---

## Suggested next block

After Phase 19, do not jump directly into complexity.

Recommended next block:

```text
7A — Integration Health / Contract Freeze
7B — Edge Report artifact export
7C — CLI command for full research run
7D — Fixture expansion / multi-asset replay
7E — Cost/slippage research model
```

The next best phase is likely:

`7A — Integration Health / Contract Freeze`

Purpose:
- reduce duplicated safety stamping
- centralize research-only artifact assertions
- check schema consistency
- create one canonical end-to-end test
- prepare for more realistic research replay
