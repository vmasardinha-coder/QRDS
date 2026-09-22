# F-XAGENT-DISAGREE + F-XAGENT-VETO — preregistered handoff

Date: 2026-09-21

## Purpose

Extract the economically reusable mechanisms from TradingAgents and AI Hedge Fund without integrating an LLM-agent framework:

1. `F-XAGENT-DISAGREE` — disagreement among independent available signals as an uncertainty state.
2. `F-XAGENT-VETO` — independent risk veto / abstention semantics where unavailable evidence is never silently treated as neutral.

No external LLM output, provider-specific prompt, model score, PnL or winner parameter is imported.

## F-XAGENT-DISAGREE

### Input contract

- at least 3 independent available component signals;
- each signal is already normalized by its producer into `[-1, +1]`;
- missing/unavailable components are excluded from numeric aggregation but counted explicitly;
- the family does not define how upstream component signals are generated.

### Frozen features

For available values `x_i`:

- `available_count`
- `unavailable_count`
- `availability_fraction`
- `consensus_mean = mean(x_i)`
- `consensus_abs = abs(consensus_mean)`
- `disagreement_std = population_std(x_i)`
- `pairwise_disagreement = mean(|x_i-x_j|/2)` across all unordered pairs; bounded `[0,1]`
- `sign_split_fraction = min(n_positive, n_negative) / available_count`, where exactly zero is neither positive nor negative

No exposure multiplier, threshold, sign or return horizon is frozen here. Factory child hypotheses may later test whether high disagreement should abstain/reduce exposure only under preregistered rules.

### Eligibility

- fewer than 3 available signals => `ABSTAIN / INSUFFICIENT_INDEPENDENT_SIGNALS`
- any finite-range violation => fail closed
- unavailable is never replaced with 0

## F-XAGENT-VETO

### Input contract

Independent risk assessors emit exactly one categorical state:

- `ALLOW`
- `VETO`
- `ABSTAIN_UNAVAILABLE`

At least one assessor is required.

### Frozen aggregation

Priority is deterministic:

1. if **any** assessor emits `VETO` => aggregate `VETO`;
2. else if **any** assessor emits `ABSTAIN_UNAVAILABLE` => aggregate `ABSTAIN`;
3. else => aggregate `ALLOW`.

This directly preserves the external lesson `unavailable != neutral`.

The family emits counts/fractions for each state plus the aggregate decision. It does not decide position size, direction or economic horizon.

## Factory child hypotheses allowed later

- disagreement as entry gate;
- disagreement as exposure/risk scaler;
- disagreement spike as regime feature;
- veto as independent risk overlay on a proposed trade;
- abstention when required risk evidence is unavailable;
- interaction between disagreement and existing family confidence.

Any threshold, lookback, mapping to exposure, child-family selection or economic objective must be generated/tested under normal Factory discipline.

## Explicit prohibitions

- no mocked TradingAgents benchmark presented as economic evidence;
- no LLM-provider output becomes canonical truth;
- no unavailable evidence coerced to neutral/zero;
- no imported external performance;
- no Factory runtime/registry/order/capital mutation in this handoff.

## Safety

`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `REAL_CAPITAL_BRL=0`, `ORDERS=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `FACTORY_RUNTIME_UNTOUCHED=true`.

## Disposition

`F-XAGENT-DISAGREE = FAMILY_SPEC_READY / DETERMINISTIC_TRANSFORM_VALIDATION_REQUIRED`

`F-XAGENT-VETO = FAMILY_SPEC_READY / DETERMINISTIC_TRANSFORM_VALIDATION_REQUIRED`
