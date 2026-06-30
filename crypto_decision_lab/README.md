# crypto_decision_lab — QRDS/QOS v1.0

Quant Research & Design Specification / Quant Operating System.

**Mode: `INTERACTIVE_RESEARCH_ONLY`** — no real API keys, no real accounts,
no real orders, no real capital, no operational execution. Ever.

## Status

This is the consolidated repository scaffold (Sprint 6A). Core safety gates
and the exchange connector layer are implemented and tested. Research modules
(`dql/`, `features/`, `regimes/`, `targets/`, `research/`, `backtest/`,
`risk/`, `paper/`, `pipelines/`, `dashboard/`, `export/`) are stubs awaiting
migration from prior sprint packages — see `docs/gates/sprint_gate_log.md`
for migration progress.

## Exchange roles

| Exchange | Role |
|---|---|
| Binance | `SIMULATION_FIXTURE_REPLAY` |
| OKX | `PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH` |
| Bybit | `PENDING_BLOCKED_BY_403` |

See `docs/EXCHANGE_ROLE_POLICY.md` and `docs/BYBIT_403_BACKLOG.md`.

## Setup

```bash
python -m pip install -e ".[dev]"
pytest -q
```

## Run the safety test suite

```bash
pytest tests/safety -v
```

## Optional dashboard

```bash
python -m pip install -e ".[dashboard]"
streamlit run scripts/run_interactive_research_dashboard.py
```

## Safety policy

See `docs/SAFETY_POLICY.md` — read this before touching `exchanges/` or
`safety/`.
