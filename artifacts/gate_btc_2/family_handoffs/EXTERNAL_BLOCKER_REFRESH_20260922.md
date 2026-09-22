# BTSE 2.0 external blocker refresh — 2026-09-22

## Scope

Re-check whether recent QRDS/Factory changes unlock any of the remaining external-family HOLDs. This is an external-lane adjudication only. It does not modify Factory runtime, source registries, engines, orders, capital, survivor status, or canonical parameters.

## Canonical repository state reviewed

Main at review start: `93718e9ea332421976724478e5a1c8b3674b1372`.

Recent Factory work corrected DELTA V12 cross-sectional normalization so each historical day is measured only over assets admitted on or before that day, using explicit price provenance. This materially improves causal/provenance semantics for that specific prospective ledger.

That change does **not** create the broad historical PIT cross-sectional feature panel required by `F-XFACTOR-NONLINEAR`.

## 1. F-XFACTOR-NONLINEAR / Qlib

Required input remains:

`HISTORICAL_PIT_CROSS_SECTIONAL_QRDS_FEATURE_PANEL`

Current result:

`BLOCKED_AWAITING_HISTORICAL_PIT_CROSS_SECTIONAL_PANEL`

Reason:

- The recent V12 correction supplies day-level admission provenance for a narrow prospective engine ledger.
- It does not provide a sufficiently long historical cross-sectional QRDS feature matrix with original as-of availability semantics for all features/assets.
- Retroactive historical membership or features may not be inferred merely because a later snapshot contains older price history.
- Therefore the external Qlib benchmark cannot be translated into QRDS economic credit and no backfilled panel may be fabricated.

Important distinction:

`causal cross-section on a prospective ledger != historical PIT factor-research panel`.

## 2. F-XNLP-SENTIMENT / FinBERT

Required input remains:

`ADMISSIBLE_TIMESTAMPED_CRYPTO_NEWS_HISTORY_WITH_AVAILABILITY_SEMANTICS`

Repository search found no newly added corpus satisfying publication/availability-time semantics for historical crypto news.

Current result:

`BLOCKED_AWAITING_TIMESTAMPED_CRYPTO_NEWS_EVIDENCE`

The standalone FinBERT classifier capability remains valid; crypto-news economic generalization remains unproven.

## 3. TradingAgents economic benchmark

Required unlock remains either:

1. an authorized hosted LLM credential available to reproducible research CI, or
2. a version-pinned reproducible local/remote OpenAI-compatible or Ollama endpoint with frozen model revision/hash and decoding.

Repository search found no newly committed provider credential contract or reproducible inference endpoint.

Current result:

`HOLD / PROVIDER_REPRODUCIBILITY_BLOCKED_FOR_ECONOMIC_BENCHMARK`

The deterministic mechanisms already extracted from TradingAgents — `F-XAGENT-DISAGREE` and `F-XAGENT-VETO` — remain valid Factory handoffs and do not depend on reopening this blocker.

## 4. New-family check

No newly merged external capability in the reviewed interval establishes a genuinely new economic family beyond the current handoff inventory.

Do not install another external platform merely to increase system count.

## Non-canonical observation

At review time PR #900 is open and describes a prospective V13 successor with `not_before: 2026-09-22`, null anchor, backdating prohibited, and no inherited V12 evidence. Because the PR is not merged at this review point, it is not treated as canonical evidence. Its stated design is nevertheless consistent with the conclusion above: prospective causal collection is useful, but it is not historical PIT backfill authority.

## Disposition

External BTSE remains at the scientific frontier under current evidence:

- ready handoffs should be adjudicated by the Factory;
- blocked families reopen only when their exact evidence blocker is genuinely satisfied;
- failed frozen hypotheses remain tombstoned;
- no busywork integration is justified.

Safety boundary: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `REAL_CAPITAL_BRL=0`, `ORDERS=0`, `NO_BACKFILL=true`, `NO_RETUNE=true`, `FACTORY_RUNTIME_UNTOUCHED=true`.
