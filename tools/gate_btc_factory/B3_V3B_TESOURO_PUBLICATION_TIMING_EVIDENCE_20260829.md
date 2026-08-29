# B3 v3b — Tesouro Direto publication timing evidence

Date: 2026-08-29
Scope: source qualification only; no economics; no family activation.

## Official source identity

- Provider: Tesouro Nacional / Tesouro Transparente.
- Dataset: Taxas dos Títulos Ofertados pelo Tesouro Direto.
- CKAN resource id: `796d2059-14e9-44e3-80c9-2d9e30b405c1`.
- Historical snapshot is re-fetched and SHA-256 hashed by the v3b qualifier on every run.

## Official temporal metadata

The official Tesouro Transparente metadata for this dataset states:

- temporal frequency: daily;
- timeliness: publication on the first business day after the close of the federal public bond secondary market;
- series in progress.

Official metadata resource:
`https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/1a8eb2e3-4902-4a38-a1eb-6410f23d90de/download/Taxa.pdf`

Official dataset page:
`https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto`

## Frozen causal interpretation

The official metadata proves that a reference-date observation is not contemporaneously available during that same market session. Because the metadata does not guarantee an exact intraday publication timestamp for every historical observation, v3b applies the stricter rule:

`REFERENCE_DATE_VALUE_USABLE_FROM_SECOND_B3_SESSION_ONLY_UNTIL_REVISION_SEMANTICS_PROVEN`

This intentionally sacrifices freshness rather than risk look-ahead.

## Remaining unresolved gate

Historical revision/immutability semantics are not proven by the currently available official metadata. The public CKAN resource is a living file and can be updated. Therefore a current historical snapshot, even when hashed, must not be treated as immutable point-in-time history unless revision semantics or archived historical versions are independently proven.

Status remains:

- source identity: qualified;
- 2020–2024 coverage: qualified;
- publication direction/timing: qualified with conservative lag;
- historical revision semantics: `UNRESOLVED_CURRENT_SNAPSHOT_MAY_BE_REVISED`;
- Stage B: unauthorized;
- H2890+: unauthorized;
- economics: unauthorized.

## Safety

`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `NO_COUNTER_RESET=true`, `FAIL_CLOSED=true`, `H1_ECONOMICS_READ=false`.
