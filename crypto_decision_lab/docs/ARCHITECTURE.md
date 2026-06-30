# QRDS / QOS — Architecture

## Principle

Build a research-only pipeline first, with hard safety boundaries.

## High-level architecture

```text
Input Layer
  local fixtures
  OKX-shaped public fixtures

Data Adapter Layer
  public adapter contract
  OKX public adapter

Storage Layer
  public data cache

Research Pipeline Layer
  DQL
  features
  regimes
  targets
  integrated dataset

Artifact Layer
  export
  manifest
  bundle
  registry

Validation Layer
  walk-forward splitter

Model Layer
  constant mean baseline

Replay Layer
  hypothetical backtest skeleton

Report Layer
  Edge Report v1
```

## Safety architecture

Every boundary must preserve:

```text
research_allowed = True
operational_decision_allowed = False
api_key_required = False
api_key_present = False
account_connection_required = False
orders_generated = False
real_capital_used = False
```

Later consolidation should centralize these stamps and assertions.
