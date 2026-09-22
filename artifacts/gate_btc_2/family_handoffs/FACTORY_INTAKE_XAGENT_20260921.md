# Factory intake — XAGENT families

Date: 2026-09-21

## Purpose

Hand off the reusable mechanisms already extracted from TradingAgents / AI Hedge Fund to the QRDS Factory **without integrating either platform** and without granting any economic credit.

This document is the boundary between lanes. The BTSE external lane defines semantics and admissible child-search dimensions. The Factory lane binds those mechanisms to concrete existing QRDS signals/risk assessors, generates child hypotheses, runs canonical economics, and decides whether anything survives.

## F-XAGENT-DISAGREE

Status: `READY_FOR_FACTORY_CHILD_GENERATION`.

The first Factory generation must treat disagreement as **uncertainty**, not as trade direction.

Required input:
- at least 3 available normalized signals in [-1, +1];
- signals must represent distinct evidence/family channels;
- unavailable signals are excluded and counted, never replaced by zero.

Frozen feature semantics remain those in `F_XAGENT_DISAGREE_FAMILY.json`.

Admissible first-generation search dimensions:
- role: abstention/exposure gate;
- uncertainty metric: `disagreement_std`, `pairwise_disagreement`, or `sign_split_fraction`;
- causal rolling quantile threshold: 0.25 / 0.50 / 0.75;
- causal lookback: 168 / 720 bars;
- action: full base position or flat.

The trade direction must come from the base strategy. The disagreement layer may only decide whether the base decision is trusted enough to remain active.

Comparator: identical base strategy, dates, costs and execution, with the disagreement layer disabled.

## F-XAGENT-VETO

Status: `READY_FOR_FACTORY_CHILD_GENERATION_AFTER_ASSESSOR_BINDING`.

The Factory must bind at least two independent risk assessors to categorical states:
- `ALLOW`
- `VETO`
- `ABSTAIN_UNAVAILABLE`

Frozen semantic priority:

`VETO > ABSTAIN_UNAVAILABLE > ALLOW`

Admissible first-generation search dimensions:
- role: entry-veto overlay only;
- veto policy: any veto / majority veto;
- unavailable policy: abstain if any unavailable / abstain if majority unavailable;
- position mapping: ALLOW keeps the base position; VETO or ABSTAIN goes flat.

No hidden score averaging is allowed across categorical states. Unavailable evidence can never be silently converted into ALLOW.

Comparator: identical base strategy, dates, costs and execution, with the veto layer disabled.

## Scientific boundary

The following remain external-lane responsibilities:
- provenance;
- feature semantics;
- deterministic transformations;
- bounded child-search grammar.

The following belong exclusively to the Factory lane:
- selecting concrete existing QRDS inputs;
- generating actual child hypotheses;
- canonical causal backtests;
- cost/execution treatment;
- survivor adjudication;
- any later runtime promotion.

No TradingAgents LLM output, provider-specific decision, prompt, external PnL or claimed winner is imported.

## Non-negotiable controls

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_BACKFILL=true`
- `NO_RETUNE=true`
- no post-hoc sign flip;
- no survivor claim before canonical Factory adjudication;
- this handoff does not modify Factory runtime, V2A/PIT registry, canonical parameters or orders.

## Disposition

`XAGENT_FACTORY_INTAKE = READY_FOR_FACTORY_LANE`
