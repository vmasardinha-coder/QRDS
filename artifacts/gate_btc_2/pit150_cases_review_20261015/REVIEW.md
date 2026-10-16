# PIT150 — revisão dos 25 casos em 15/10/2026

**P0.2 continua aberto.** USDGO ganhou uma rota Bitget com 200 dias completos comprovados e reparo testado. Os outros 24 casos continuam abertos. USDY já tinha reparo pela PR1168. O último recibo autoritativo permanece 124/150; este relatório não incrementa cobertura.

| Caso | Estado | Evidência e próxima ação |
|---|---|---|
| BUIDL (blackrock-usd-institutional-digital-liquidity-fund) | FUND_SCOPE_REVIEW | Current CoinGecko ticker discovery returned no markets; prior issuer/fund adjudication remains applicable, no public exact execution tape established. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Review fund execution/NAV contract under approved future-D0 exclusion rule; no rewrite of current150. |
| EURSAFO (spiko-amundi-overnight-swap-fund-eur) | FUND_SCOPE_REVIEW | No current listed ticker market; September adjudication identifies subscriptions/redemptions at NAV, not public spot execution. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Apply existing structural adjudication only in a separately frozen future D0. |
| USDGO (usdgo) | SOURCE_REPAIR_READY | Bitget USDGOUSDT200unique consecutive UTC days2026-03-29 through2026-10-14, exact SOLmint and currency2091; MEXC169isnotglobaldepth. Integrate qualified route effectivecutoff2026-10-15 and confirm first real daily admission receipt. |
| BCAP (blockchain-capital) | FUND_SCOPE_REVIEW | Current ticker discovery empty; historical BCAP ATS/securities route has no established free public exact tape. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Retain source exhaustion record; review future-D0 scope with immutable exclusion ledger. |
| OUSD (open-usd) | SHORT_SOURCE_HISTORY | Exact OpenUSD Kraken route15 completed days from2026-09-30; OriginUSD is a different identity. 185additional days if uninterrupted; earliest depth200 2027-04-17, subject to full QA. |
| USTB (superstate-short-duration-us-government-securities-fund-ustb) | FUND_SCOPE_REVIEW | Current ticker discovery empty; exact fund token cannot be replaced by Treasury ETF or NAV observations. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Exact public secondary tape or future-D0 structural scope. |
| EUTBL (eutbl) | FUND_SCOPE_REVIEW | September exact Spiko NAV/subscription adjudication; initial refresh returned429 and subsequent bounded retry succeeded. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Preserve dated adjudication; future-D0 scope only. |
| PRL (pearl-2) | SHORT_SOURCE_HISTORY | Fixed BigONE period parameter toDAY1: Pearl route112closed days from2026-06-25. Ourbit139days but spot disabled; Gate/MEXC Perle is wrong coin. BigONE needs88additional completed days if uninterrupted; earliest depth200 2027-01-10. Do not substitute Perle. |
| JAAA (janus-henderson-anemoy-aaa-clo-fund) | FUND_SCOPE_REVIEW | Exact fund liquidity/redemption is not deJAAA wrapper spot tape; current bounded retry succeeded. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Preserve exact identity; future-D0 scope only. |
| KAU (kinesis-gold) | ACCESS_IDENTITY_REVIEW | Exact Kinesis native asset markets discovered; documented OHLC endpoint returned403 without API keys. Authorized native source access or a demonstrably public exact tape;403 alone does not establish structural exclusion. |
| YLDS (ylds) | FUND_EXECUTION_SEMANTICS_REVIEW | Figure4372public matches across200days; marketTypeFUND, proTradeAvailablefalse, fixed-price product. Clarify subscription/redemption versus secondary execution semantics; do not infer eligible spot history from matches count. |
| A7A5 (a7a5) | PUBLIC_ARCHIVE_DEPTH_BLOCK | Exact DEXpool public response has183consecutive days; older API history401. A7A5 independent nativeRPC archive explicitly requires personal token. Obtain authorized historical access or preserve and qualify enough additional completed observations; waiting alone does not expand a rolling183-day endpoint. |
| HASH (hash-2) | SOURCE_CONSISTENCY_BLOCK | Figure5673unique trades across200days and2340physicalhours; four independently reproduced hourly-volume disagreements. Resolve source consistency before admission; no arbitrary trade-ID close ordering. SeeHASH_AUDIT.json. |
| SOFID (sofiusd) | SHORT_SOURCE_HISTORY | Bullish paginated public SOFIDUSDC history has115unique consecutive completed UTC days,2026-06-22 through2026-10-14, no gaps. Kraken41days is not the global maximum. 85additional completed days would reach200on2027-01-07 if uninterrupted; exact identity, quote-volume semantics and full QA still required. No source admission now. |
| USDAI (usdai) | PUBLIC_ARCHIVE_GAPS_BLOCK | Exact DEXpool returned183rows/182unique days with12missing calendar days; older API history401. Recover exact physical missing executions/history or retain source rejection; no forward-fill or alternate coin. |
| REUSD (re-protocol-reusd) | PUBLIC_ARCHIVE_DEPTH_BLOCK | Exact DEXpool public response has183consecutive days; older API history401. A7A5 independent nativeRPC archive explicitly requires personal token. Obtain authorized historical access or preserve and qualify enough additional completed observations; waiting alone does not expand a rolling183-day endpoint. |
| JTRSY (janus-henderson-anemoy-treasury-fund) | FUND_SCOPE_REVIEW | Exact JTRSY fund differs from deJTRSY wrapper; bounded retry succeeded. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Preserve exact identity; future-D0 scope only. |
| OUSG (ousg) | FUND_SCOPE_REVIEW | Existing exact fund adjudication; current bounded retry succeeded. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Review public secondary tape or future-D0 scope;429 cannot justify exclusion. |
| APXUSD (apxusd) | SHORT_SOURCE_HISTORY | Kraken178 completed days,2026-04-20 through2026-10-14. 22additional completed days if uninterrupted; earliest depth200 2026-11-05, subject to full QA. |
| OHM (olympus) | PUBLIC_ARCHIVE_GAPS_BLOCK | Exact DEXpool returned183rows/182unique days with31missing calendar days; older API history401. Recover exact physical missing executions/history or retain source rejection; no forward-fill or alternate coin. |
| SAFO (safo) | FUND_EXECUTION_SEMANTICS_REVIEW | Exact coin_idsafo has no ticker markets in successful fresh response; name is SpikoAmundiOvernightSwapFund. Exact fund execution contract review, not ticker-only substitution or automatic exclusion. |
| KOGE (bnb48-club-token) | PUBLIC_ARCHIVE_DEPTH_BLOCK | Exact DEXpool public response has183consecutive days; older API history401. A7A5 independent nativeRPC archive explicitly requires personal token. Obtain authorized historical access or preserve and qualify enough additional completed observations; waiting alone does not expand a rolling183-day endpoint. |
| KAG (kinesis-silver) | ACCESS_IDENTITY_REVIEW | Native Kinesis OHLC403; MEXC175-day ERC20 route is a separately issued KMS Labs wrapper under existing adjudication. Resolve native-versus-wrapper identity and authorized source access; do not admit wrapper or fill25missing days. |
| USX (usx) | PUBLIC_ARCHIVE_DEPTH_BLOCK | Exact DEXpool public response has183consecutive days; older API history401. A7A5 independent nativeRPC archive explicitly requires personal token. Obtain authorized historical access or preserve and qualify enough additional completed observations; waiting alone does not expand a rolling183-day endpoint. |
| PC0000031 (tradable-na-rent-financing-platform-sstn) | FUND_SCOPE_REVIEW | Private financing/security identity in current150; no200-day exact public tape established. Current bounded retry succeeded. Latest bounded retry succeeded with an empty ticker-market list; this is not proof of global absence. Existing exact structural review, then future-D0 scope; no proxy. |

## Limites da conclusão

Os documentos de setembro continuam expressamente datados. As consultas inicialmente limitadas por HTTP429 tiveram retry público bem-sucedido, com a resposta original preservada. Uma lista vazia de mercados não prova ausência global de fonte. A regra de exclusão estrutural de 04/09 só permite efeito em um novo D0 futuro com ledger imutável: não transforma 124/150 histórico em 124/124.

## Figure: 33 dias eram a janela solicitada

A ampliação recuperou 200 dias com negócios públicos para HASH e YLDS. No HASH, o auditor cruza 5.673 negócios únicos com 2.340 candles TRADE horários e bloqueia quatro divergências de volume reproduzidas por consultas independentes. Preços diferentes no mesmo nanossegundo não são ordenados pelo ID: o close horário do próprio provedor precisa pertencer ao conjunto de últimos negócios físicos. YLDS permanece separado por sua semântica de fundo, sem admissão de fonte.

## Provas reproduzíveis

- FIGURE_RAW.zip: páginas públicas, identidade HASH, candles horários e consultas independentes das quatro horas divergentes.
- HASH_AUDIT.json: 200 dias, 5.673 negócios, 2.340 horas, quatro divergências, source_admission=false.
- SOURCE_DISCOVERY_RAW.zip: consultas atuais e retries de mercados/identidade/profundidade, inclusive as recusas HTTP.
- CASE_LEDGER.json: 25 casos revisados, um reparo novo de fonte, 24 fontes não resolvidas, crédito zero.
- ../pit150_usdgo_bitget_20261015/: identidade, mint, 200 candles UTC e qualificação USDGO.
- SHA256.json: hashes dos arquivos desta revisão.

## Fontes primárias

- API pública Figure: https://www.figuremarkets.dev/api-docs/apis/public/
- Anúncio Bitget e mint Solana USDGO: https://www.bitget.com/support/articles/12560603859340
- Exemplo oficial Kinesis com autenticação: https://github.com/bullioncapital/kinesis-api/blob/main/v1/kinesis_api_example.py
- Paginação pública Bullish: https://docs.exchange.bullish.com/rest/general/pagination/
- Lançamento SOFID Bullish: https://www.bullish.com/eu/news-insights/bullish-becomes-the-first-centralized-exchange-to-list-sofiusd-sofis-bank-issued-us-dollar-stablecoin
