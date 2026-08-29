# B3 v3b — BDI archive regime evidence — 2026-08-29

## Scope
Evidence-only follow-up to PR #313 / Issue #293. No economics, family activation, source admission, backfill, retune, counter reset, clock mutation, order path, or capital change.

Safety remains:
`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `NO_COUNTER_RESET=true`, `FAIL_CLOSED=true`.
H1/H31 and all prospective ledgers remain isolated. MT5 remains `INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY`.

## Machine probe result from PR #313
Workflow run `33270355818`, artifact `gate-btc-b3-v3b-bdi-archive-probe-33270355818`, artifact digest `sha256:1d749d1f101e0febcf8e5ee8f9ed58e96f3ef45a8fa00b793906566a5b473514`.

The exact candidate URL contract
`https://arquivos.b3.com.br/bdi/download/bdi/{date}/BDI_00_{yyyymmdd}.pdf`
returned:

- 2020-01-02: HTTP 500 — unqualified
- 2021-01-04: HTTP 500 — unqualified
- 2022-01-03: HTTP 500 — unqualified
- 2023-01-02: official PDF retrieved, 4,053,704 bytes, SHA-256 `6d153cc5fc4cae24c8cf9b0138517cd73919090dfeace855c42d41f5cc5e5232`
- 2024-01-02: official PDF retrieved, 14,703,793 bytes, SHA-256 `32204639436bf0d06ae395efdfb6e544f89d2f15351c5f05d5ecb0297356a2e0`

Therefore the exact post-redesign URL contract is **not proven** for 2020–2022 and must not be extrapolated backward.

## Official B3 publication-regime evidence
B3 published on 2022-03-29 that the BD/BDI consultation experience would change starting 2022-04-04, with navigable web consultation and PDF/CSV downloads. This is direct evidence of a publication-system regime change around April 2022 and explains why one modern archive URL template cannot be assumed to cover earlier years.

Official B3 source:
`https://www.b3.com.br/pt_br/noticias/boletim-diario-do-mercado.htm`

B3 also states in 2023 notices that bulletins older than 20 days are available in the **Acervo B3** in PDF format, establishing an official archival route distinct from the recent BDI web surface.

Official B3 sources:
- `https://www.b3.com.br/pt_br/noticias/boletim-diario-8AE490C995C8A43A019614B21FCA7472.htm`
- `https://www.b3.com.br/pt_br/noticias/boletim-diario-8AA8D0CC8803C8CB01885493913F501F.htm`

## Scientific interpretation
The 2020–2022 HTTP failures are **not sufficient evidence of historical data absence**. They are compatible with an archive-contract/regime mismatch. Accordingly they must not be classified as definitive `DATA_GAP` until the official Acervo B3 route is itself qualified.

Current status:
- post-redesign BDI archive identity: partially demonstrated (2023–2024 sentinels only)
- pre-redesign / transition archive route: `UNRESOLVED_OFFICIAL_ACERVO_B3_CONTRACT`
- full 2020–2024 business-day coverage: not proven
- schema stability across publication regimes: not proven
- publication timing: not qualified
- revision/errata immutability: not qualified
- contract identity / roll continuity: not qualified
- `source_qualified=false`
- `stage_b_authorized=false`
- `family_ids_authorized=false`
- `h2890_plus_authorized=false`
- `economics_authorized=false`

## Next admissible action
Qualify the official Acervo B3 retrieval contract for representative 2020, 2021 and pre/post-2022-04-04 dates. Record exact provenance, final URL, raw-byte SHA-256, content type, schema/layout identity, timezone/reference-date semantics, and coverage. Do not reconstruct missing clocks and do not use MT5 as a primary substitute.
