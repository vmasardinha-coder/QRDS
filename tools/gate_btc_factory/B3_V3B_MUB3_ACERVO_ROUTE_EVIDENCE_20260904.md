# B3 v3b — MUB3 Acervo route evidence — 2026-09-04

## Scope
Source-qualification-only continuation of Issue #293 and the fail-closed BDI archive investigation. No economics, family activation, source admission, backfill, retune, counter reset, clock mutation, order path, or capital change.

Safety remains:
`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `NO_COUNTER_RESET=true`, `FAIL_CLOSED=true`.
H1/H31 and all prospective ledgers remain isolated. MT5 remains `INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY`.

## New route evidence
The prior canonical blocker correctly established that modern `arquivos.b3.com.br/bdi/download/bdi/...` URL semantics cannot be extrapolated to 2020–2022 and that B3 states older bulletins are available through Acervo B3.

A fresh audit on 2026-09-04 identified the currently reachable archive surface:

- legacy/public entry: `https://mub3.org.br/acervo`
- observed redirect/final public surface: `https://mub3.org.br/centro-referencia/acervo`
- operator: Museu da Bolsa do Brasil (MUB3), with B3 institutional sponsorship/association shown on the public page
- public UI exposes search text, record type, date-from/date-to and ordering controls

Independent corroborating guidance from Petrobras investor relations explicitly instructs users seeking historical B3 quotations from 1986 onward to use `https://mub3.org.br/acervo`, choose the period, and download the `Boletim Diário de Informações` for the requested date; if a bulletin is unavailable, it directs users to B3 historical quote series instead.

Relevant public sources:
- `https://mub3.org.br/acervo`
- `https://www.investidorpetrobras.com.br/servicos-ao-investidor/investidor-individual/perguntas-frequentes/`
- B3 notices already frozen in `B3_V3B_BDI_ARCHIVE_REGIME_EVIDENCE_20260829.md` stating bulletins older than 20 days are available through Acervo B3.

## Scientific interpretation
This materially narrows the previous blocker:

- official/archive destination identity: **identified as MUB3 Acervo public surface**
- machine-retrieval contract for date-filtered BDI records: **not yet qualified**
- exact immutable file URLs for representative 2020, 2021 and pre/post-2022-04-04 dates: **not yet qualified**
- raw-byte SHA-256 for those representative files: **not yet recorded**
- schema/layout identity across regimes: **not yet qualified**
- timezone/reference-date semantics: **not yet qualified**
- full 2020–2024 business-day coverage: **not proven**
- publication timing: **not qualified**
- revision/errata immutability: **not qualified**
- contract identity / roll continuity: **not qualified**

Therefore this evidence MUST NOT be interpreted as source admission and MUST NOT authorize Stage B or H2890+.

Current state remains:
- `source_qualified=false`
- `stage_b_authorized=false`
- `family_ids_authorized=false`
- `h2890_plus_authorized=false`
- `economics_authorized=false`

## Next admissible action
Reverse-engineer only the public MUB3 archive search/download request contract sufficiently to retrieve representative BDI documents for 2020, 2021 and both sides of the 2022-04-04 publication-regime transition. For every retrieved file record final URL, content type, raw bytes, SHA-256, publication/reference date, visible schema/layout identity and coverage result.

If the archive UI does not expose a stable, freely auditable machine retrieval contract, record that limitation explicitly; do not infer absence of historical bulletins, do not reconstruct clocks, and do not substitute MT5 or non-official data as primary history.
