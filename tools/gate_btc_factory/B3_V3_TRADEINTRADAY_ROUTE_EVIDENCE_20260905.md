# B3 v3 — TradeIntradayFile route evidence — 2026-09-05

## Scope
Source-qualification-only continuation for Issue #289 / H2730-H2739. No economics, family activation beyond the already-frozen v3 source gate, source admission, backfill, retune, counter reset, prospective feedback, order path, or capital change.

Safety remains frozen:
`RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `NOT_APPROVED=true`, `ENGINE_FEED=false`, `ORDERS=0`, `REAL_CAPITAL=0`, `NO_RETUNE=true`, `NO_BACKFILL=true`, `NO_COUNTER_RESET=true`, `FAIL_CLOSED=true`.
H1/H31 and all prospectives remain isolated. MT5 remains `INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY` and is not a primary source or clock-reconstruction mechanism.

## Official B3 product/schema evidence
Fresh source audit on 2026-09-05 confirms that B3 documents a public listed-products trade-by-trade file named `DD-MM-AAAA_NEGOCIOSAVISTA (TradeIntradayFile)`.

Official B3 glossary states that the file reports all trades from the session at negócio-a-negócio level, is published the following morning, and is delivered as a ZIP containing a `.txt`. The schema includes the fields necessary for the v3 primary-source contract, including instrument/ticker identity, trade price, quantity, trade identifier/action semantics and event time. Existing official B3 documentation also places `Negócio a negócio – Listados` in the current Boletim Diário do Mercado public-data hierarchy.

Official references:
- `https://www.b3.com.br/data/files/14/42/28/31/FEC4A8103234E0A8AC094EA8/Glossario_NegociosListados_PT.pdf`
- `https://www.b3.com.br/data/files/28/C7/3A/11/33F7A9105B12E5A9AC094EA8/CE%20007-2025-VTEC%20MELHORIAS%20NO%20ACESSO%20AOS%20DADOS%20NO%20SITE%20B3_PT.pdf`
- `https://www.b3.com.br/data/files/24/92/1D/71/773CB9109B5E99B9AC094EA8/CE%20001-2026-VTEC_NOVA%20DATA%20PARA%20DESCONTINUACAO%20DA%20PAGINA%20DE%20DADOS%20PUBLICOS_PT.pdf`

## Candidate physical retrieval route
A public implementation example independently documents the date-addressed route pattern:

`https://arquivos.b3.com.br/rapinegocios/tickercsv/YYYY-MM-DD`

and shows a successful 2024-10-04 retrieval yielding `04-10-2024_NEGOCIOSAVISTA.txt` after ZIP extraction.

This third-party example is route-discovery evidence only. It is NOT sufficient to qualify the B3 primary source by itself and does not replace official provenance requirements.

Corroborating route-discovery reference:
- `https://medium.com/@cesarmontenegrosilva/optimizing-big-data-pipelines-the-advantages-of-using-parquet-files-for-data-storage-and-62f7a47888c6`

## Scientific interpretation
The following parts of the v3 source contract are now materially better identified:

- official product identity: `Negócio a negócio – Listados / TradeIntradayFile`
- official file naming semantics: `DD-MM-AAAA_NEGOCIOSAVISTA`
- official publication cadence: following morning for prior session
- official delivery container: ZIP with `.txt`
- trade-level schema class: confirmed
- current public date-addressed candidate route: identified

The following remain unqualified and therefore fail closed:

- reproducible raw retrieval for representative historical dates in every required year 2020, 2021, 2022, 2023 and 2024
- raw-byte SHA-256 for representative and eventually complete required files
- full business-session coverage and explicit missingness map for 2020-2024
- exact schema/version continuity across the 2020-2024 archive
- raw timezone semantics and deterministic normalization contract for every regime
- `new/delete` cancellation/revision handling verified against physical files
- duplicate/event identity policy validated against physical rows
- contract identity / front-contract mapping audit for WIN/WDO futures
- historical publication availability/causality consistency
- revision/errata/immutability behavior for archived files

Therefore current authority remains:

- `source_qualified=false`
- `source_ready_for_economics=false`
- `economics_authorized=false`
- `generation=H2730-H2739`
- `status=WAITING_OFFICIAL_TICK_SOURCE`

No `DATA_GAP` is declared from this evidence. The correct state is `SOURCE_ROUTE_IDENTIFIED_PHYSICAL_HISTORICAL_QUALIFICATION_PENDING`.

## Next admissible action
Physically probe the exact candidate route on preregistered representative dates spanning 2020-2024. For each response, preserve final URL, HTTP/content metadata, raw ZIP bytes, internal filename(s), raw `.txt` bytes, SHA-256, row/schema sample, raw timestamp semantics, instrument identity sample, duplicate/action semantics and publication/reference date. Then build a coverage audit against the frozen B3 trading calendar.

If the route fails for older regimes, continue bounded official/free source discovery before any definitive `SOURCE_DATA_GAP`. Do not use MUB3 PDF bulletins to reconstruct trade clocks and do not substitute MT5 as primary history.
