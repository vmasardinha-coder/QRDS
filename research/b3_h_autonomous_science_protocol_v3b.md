# GATE BTC B3 Autonomous Science Protocol v3b

Status: SOURCE_QUALIFICATION_PREREGISTERED_BEFORE_ANY_V3B_ECONOMICS
Issue: #293

Purpose: continue autonomous B3 research after the finite OHLCV v1/v2 grammar ended at H2729 and the separately preregistered tick-microstructure v3 frontier H2730-H2889 failed closed at primary-source qualification. V3b must use materially distinct official/free observed cross-market state and must not alter, reopen or proxy the frozen tick-v3 protocol.

## Immutable inheritance

- H170-H2729 remain permanently governed by v1/v2 and their rejection ledger.
- H2730-H2889 remain `FAIL_CLOSED_SOURCE_DATA_GAP` unless the exact frozen official raw B3 event source becomes auditable; v3b cannot rescue or reinterpret them.
- discovery window remains 2022-2024; independent replication remains 2020-2021; cutoff is exclusive 2026-08-10.
- existing reference/stress costs, delayed-entry rule, stability gates, concentration gates and survivor rules remain unchanged unless a later amendment is preregistered before economics solely because a newly qualified observed-data cadence mechanically requires it.
- H1 economics and all partial prospective economics remain unread.

## Stage A — source qualification only

No v3b family IDs or economics are authorized by this document. The first stage is intentionally non-economic: prove exact official/free observed series and their historical point-in-time availability.

Priority source classes, in order:

1. Banco Central do Brasil official PTAX / exchange-rate data;
2. Banco Central do Brasil official interest-rate / monetary series with auditable publication timing;
3. Tesouro Nacional official sovereign-rate / curve observations with reproducible historical publication semantics;
4. B3 public daily consolidated open-interest, settlement, instrument, roll or related reports when exact historical files and contract identity are available without paid redistribution;
5. other official public cross-market series only if economically distinct and documented before any result is read.

For every candidate series the qualifier must persist:

- provider and official endpoint/product name;
- exact immutable series identifier, symbol or file naming contract;
- raw-response or raw-file SHA-256 for bytes actually used;
- parser/schema version and raw field names;
- timezone, observation date, reference date and publication timestamp semantics;
- historical coverage and missingness for 2020-2024 at minimum;
- duplicate/revision policy and deterministic dedupe rule;
- point-in-time availability proof showing the value was knowable before the B3 decision session in which it could be used;
- observed-versus-derived classification;
- license/terms/public-access note;
- fail-closed reason when any field cannot be established.

A candidate without exact identifier, causal publication semantics or sufficient coverage remains `SOURCE_UNQUALIFIED` and cannot enter a family grammar.

## Stage B — preregistration gate after source qualification

Only after Stage A proves at least one exact source class may a separate amendment freeze:

- deterministic derived feature definitions based only on already-published observations;
- explicit causal lag from source publication to B3 session use;
- finite family identities and ordering beginning no earlier than H2890;
- direction, thresholds, horizons and standardization/lookback choices;
- anti-duplication identity checks against v1/v2 and tick-v3;
- source-specific missingness and revision handling.

The amendment must be committed before any v3b economic evaluation. No outcome-guided choice is permitted.

## Diagnostic vocabulary

Source qualification and any later v3b evaluator must distinguish at least:

- `SOURCE_QUALIFIED`;
- `SOURCE_UNQUALIFIED_EXACT_ID`;
- `SOURCE_DATA_GAP`;
- `PUBLICATION_TIMING_UNPROVEN`;
- `SCHEMA_QA_FAIL`;
- `REVISION_POLICY_UNRESOLVED`;
- `CONTRACT_IDENTITY_FAIL`;
- `FEATURE_UNDEFINED_FROM_VALID_INPUT`;
- `VALID_RARITY_NO_THRESHOLD_CROSS`;
- `NO_SIGNAL`;
- `NO_TRADES`.

`NO_TRADES` is never allowed to stand in for missing/unqualified data. Thresholds may not be relaxed because a qualified feature is rare.

## MT5 boundary

MT5 may be used only after separate qualification and only as `INDEPENDENT_SECONDARY_SOURCE / CROSS_VALIDATION_ONLY`. It cannot become the primary scientific source, cannot reconstruct a missed clock, cannot substitute an unavailable official historical series and cannot create historical eligibility.

## Continuation rule

If a candidate source class fails Stage A, record the exact failure and continue to the next materially distinct official/free source class. Do not alter the failed source's definition to obtain coverage. If all reasonable official/free routes fail, leave v3b fail-closed and record the residual data frontier rather than fabricating a proxy.

## Safety

`RESEARCH_ONLY=true`
`SHADOW_ONLY=true`
`NOT_APPROVED=true`
`ENGINE_FEED=false`
`ORDERS=0`
`REAL_CAPITAL=0`
`NO_RETUNE=true`
`NO_BACKFILL=true`
`NO_COUNTER_RESET=true`
`FAIL_CLOSED=true`
`H1_ECONOMICS_READ=false`

This protocol authorizes source qualification only. It does not authorize economics, family promotion, live execution or changes to any existing scientific clock.