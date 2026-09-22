# Factory ruler audit — Item 1

Date: 2026-09-22
Scope: diagnose why H1/H31 obtained a live prospective path while the broader Factory produced very few/no additional survivors, without changing any scientific gate in this audit.

## Executive conclusion

**The Factory is not simply "too strict" in one place. It has a structural funnel problem: it treats several materially different states as terminal/non-progressing states, and it reserves forward observation almost entirely for already-proven historical survivors.**

This creates a binary flow:

`historically proven -> prospective` OR `blocked/rejected -> no learning`

That is scientifically safe but throughput-poor. It prevents causal, source-qualified, economically plausible but statistically inconclusive hypotheses from accumulating the forward evidence that could resolve uncertainty.

The recommended correction is **not to weaken survivor gates**. It is to add a zero-credit intermediate class:

`EXPERIMENTAL_PROSPECTIVE_SHADOW`

for hypotheses that are safe to observe prospectively but are not entitled to survivor status.

## What H1/H31 had that most later families did not

H1/H31 obtained an operational forward path and then accumulated hardening incrementally: causal M5 capture, live MT5 binding, fail-closed entrypoint, bounded execution front, queue/concurrency repair, economic status/export and health monitoring. In other words, they were allowed to **exist as live research objects and improve operationally while prospective evidence accumulated**.

The later Factory evolved toward a stricter model in which prospective activation generally occurs only after historical discovery + validation/replication/holdout survival. That is visible in the canonical Factory contracts that route only historical survivors into separate prospective work.

The difference is therefore not merely alpha quality. It is also **path availability**.

## Evidence from the Factory itself

### 1. Mortality was already known to be heterogeneous

PR #280 created `SCIENTIFIC_MORTALITY_RUNTIME.json` specifically to separate terminal cells into:
- `NO_TRADES`
- `INFRASTRUCTURE_OR_DATA`
- `SCIENTIFIC_REJECTION`

It also explicitly tracks discovery-qualified, replication-attempted and near-gate families. This proves the project already recognized that "not survivor" is not one scientific state.

### 2. Large portions of the backlog never reached valid economics

PR #753 reported a consolidated state with:
- 534 tracked families
- 0 survivors
- 512 B3 WIN families source-blocked
- 6 B3 daily families completed with zero survivors
- original crypto families transport-blocked and accessible crypto families waiting for activation

Therefore zero survivors cannot be interpreted as 534 clean economic rejections.

PRs #336/#374/#489/#492/#501/#502/#528 document 768 invalidated B3 families whose requalification was dominated by source qualification, strict unseen-window availability and data coverage. They were explicitly kept separate from scientific rejection.

### 3. Some families were correctly killed scientifically

Examples that should remain tombstoned under the existing rules:
- PR #684: four Regime C2 families had clean canonical source QA and were `REJECTED_DISCOVERY`.
- PR #439: EQB01-EQB10 passed source/causality QA and all failed frozen discovery economics.
- PR #680: Delta C2 volume-only families with valid source coverage were valid discovery rejections.

These are **not** evidence that the ruler is too strict. They are useful null results.

### 4. Some families were blocked before economics or by incomplete semantics

Examples:
- PR #527: WIN/WDO could not run first economics because contract-level PnL/normalization and numeric gates were not frozen.
- PR #680: funding-dependent Delta cells were data-blocked because admissible discovery funding coverage was absent.
- PR #635: BDM material did not satisfy tick-microstructure requirements.
- Qlib/FinBERT families remain blocked by historical PIT/availability requirements.

These should not receive historical survivor credit, but they are different from clean economic failure.

### 5. Current prospective routing is intentionally narrow

PRs #169/#170 and later Grammar 007/008 work use the pattern:
`historical survivor -> separate prospective zero-retroactive-credit phase`.

This is safe, but it means a hypothesis that is causal and observable yet historically underpowered/near-gate cannot accumulate forward data unless it first clears a demanding historical proof path.

## Mortality classification to use going forward

### A. VALID_SCIENTIFIC_REJECTION
Criteria:
- source/PIT/causality valid;
- adequate minimum sample/trades;
- frozen economics read legitimately;
- fails discovery/validation/replication gate.

Action: terminal tombstone. No experimental rescue of the same hypothesis. Only a materially distinct preregistered hypothesis can return.

### B. INVALID_SCIENCE_OR_DATA
Criteria:
- leakage/hindsight;
- wrong identity;
- unavailable treated as observed;
- future-known composition/revisions;
- invalid source semantics;
- fabricated/backfilled prospective evidence.

Action: no economics credit and no shadow activation until the scientific defect is repaired prospectively.

### C. DATA_OR_SOURCE_BLOCKED
Criteria:
- hypothesis is defined but required historical source/coverage does not exist or is not admissible.

Action: remain blocked for historical proof. If the source is **currently observable causally and prospectively**, the hypothesis may be eligible for experimental prospective collection after a separate forward-only source admission contract.

### D. INCONCLUSIVE_BUT_FORWARD_SAFE
Criteria:
- source identity and live availability are valid;
- causal rule is frozen;
- no leakage/backfill/retune;
- historical evidence is underpowered, near-gate, sparse, short, or unable to satisfy a proof threshold for reasons that do not invalidate prospective observation;
- execution/cost model sufficient for shadow accounting.

Action: eligible for `EXPERIMENTAL_PROSPECTIVE_SHADOW` with zero survivor/economic promotion credit.

## Recommended new intermediate stage

`IDEA -> HISTORICAL SCREEN -> EXPERIMENTAL_PROSPECTIVE_SHADOW -> CANDIDATE -> SURVIVOR -> EXECUTION`

Important: historical proof can still skip directly to CANDIDATE/SURVIVOR according to the existing contract. Experimental shadow is an **evidence-accumulation lane**, not a weaker survivor lane.

### Experimental shadow admission minimum

Must all be true:
1. mechanism and direction frozen before forward observation;
2. source identity and timestamp availability valid prospectively;
3. causal execution rule defined;
4. costs/slippage sufficient for shadow accounting;
5. no historical result-driven retune;
6. no same-hypothesis terminal clean economic rejection;
7. orders=0 and real capital=0;
8. D0 is the first observation after merged activation; no retroactive rows;
9. status explicitly says `NO_SURVIVOR_CREDIT` and `NO_PROMOTION_AUTHORITY`.

### Explicitly NOT eligible

- clean `REJECTED_DISCOVERY/VALIDATION/REPLICATION` of the same frozen hypothesis;
- leakage or invalid PIT semantics;
- fabricated/backfilled data;
- unresolved instrument/source identity;
- no executable causal rule;
- post-result threshold/sign/parameter changes.

## Audit verdict

**YES: the Factory ruler is too binary for research throughput.**

**NO: the survivor standard itself is not shown to be too strict by this audit.**

The defect is the absence of a legitimate middle state between "not historically proven" and "survivor". H1/H31 benefited from a living prospective path that later families often cannot enter.

The safest high-value change is therefore:

> Keep survivor/promotional rigor unchanged, but allow forward-safe inconclusive hypotheses to accumulate strictly prospective zero-credit evidence.

## Item 1 status

`CLOSED_WITH_ARCHITECTURAL_FINDING`

No gate, threshold, family result, survivor status, counter, source admission, order path or capital state was changed by this audit.

Next authorized project item after user review: Item 2 (formalize the legible funnel / experimental-shadow contract), followed by Item 3 (re-evaluate existing base under the new mortality classification).
