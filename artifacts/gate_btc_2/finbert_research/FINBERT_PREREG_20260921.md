# FinBERT standalone — preregistration

Date: 2026-09-21

## Purpose

Test whether `ProsusAI/finbert` provides a tangible, reproducible financial-text sentiment capability that is currently absent from QRDS/BTSE, before any attempt to use news sentiment economically.

This is external BTSE research only. It does not modify Factory logic, V2A/PIT collectors, source registries, canonical runtime, engine feeds, orders, backfill, or capital.

## Frozen external model

- model: `ProsusAI/finbert`
- Hugging Face revision: `a677990aaa7e6db63d673786a74d575cc071522e`
- task: 3-class financial sentiment classification
- labels: positive / negative / neutral
- inference: CPU, deterministic evaluation mode
- no fine-tuning
- no calibration
- no prompt engineering

## Frozen benchmark

- dataset: `atrost/financial_phrasebank`
- split: `test`
- dataset repository SHA is resolved before loading and recorded in the artifact
- the dataset is the published 64/16/20 split of Financial PhraseBank described as following the FinBERT paper
- every row in the test split is evaluated; no subsampling after labels or predictions are seen

This benchmark establishes only financial-sentiment classification capability. It does not by itself establish crypto-news generalization or trading alpha.

## Frozen primary pass rule

Standalone capability passes only if BOTH hold on the complete test split:

1. accuracy >= `0.80`;
2. macro-F1 >= `0.75`.

No class-specific threshold may substitute for either primary threshold.

## Frozen QA gates

The result is interpretable only if all hold:

1. >= `500` test examples;
2. all three gold classes are present;
3. >= `25` examples in every gold class;
4. exactly one prediction per benchmark row;
5. predicted labels belong only to positive / negative / neutral;
6. no empty source sentence;
7. duplicate row identities are reported;
8. model revision and dataset SHA are recorded;
9. raw per-row predictions and aggregate confusion matrix are emitted.

Failure produces `DATA_OR_MODEL_CAPABILITY_NOT_ESTABLISHED`.

## Frozen descriptive outputs

Report but do not redefine the pass rule from them:

- accuracy;
- macro precision / recall / F1;
- per-class precision / recall / F1 / support;
- confusion matrix;
- mean model confidence;
- number of examples and duplicate sentence count;
- model and dataset revisions;
- SHA256 of the prediction artifact.

## Integrated BTSE confrontation

If standalone capability passes, inspect QRDS/BTSE for an admissible historical crypto-news corpus that has at minimum:

- article/headline text;
- publication timestamp;
- immutable source identity or content hash;
- explicit temporal availability semantics;
- enough historical coverage to create frozen train/evaluation windows without retrospective timestamp fabrication.

If such a corpus is absent, integrated economic comparison is **blocked**, not inferred from the standalone benchmark. The clean disposition is then:

`STANDALONE_CAPABILITY_PASS / HOLD_FOR_TIMESTAMPED_CRYPTO_NEWS_EVIDENCE`

If standalone capability fails:

`REJECT_AS_SENTIMENT_COMPONENT`

No economic/alpha claim may be made from Financial PhraseBank classification accuracy.

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`
