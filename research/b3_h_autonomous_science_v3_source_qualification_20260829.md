# B3 Autonomous Science v3 — primary tick-source qualification

Date: 2026-08-29 UTC  
Issue: #289  
Follow-up: #293  
Status: `NOT_AVAILABLE / FAIL_CLOSED_SOURCE_DATA_GAP`

## Result

The preregistered H2730-H2889 tick/microstructure protocol requires official B3 raw per-trade evidence with instrument/contract identity, event timestamp, trade price and trade quantity across the frozen discovery (2022-2024) and independent replication (2020-2021) windows.

The audited free official B3 routes do not establish a public historical per-event trade tape satisfying that contract. Public historical quotation and daily bulletin routes provide daily/end-of-day or consolidated information. B3's UP2DATA documentation identifies a contracted data service and states that historical products not available on the public website are obtained through authorized distributors.

Therefore **no v3 economics may start**. H2730-H2889 is classified `SOURCE_DATA_GAP`, not `NO_TRADES`. No threshold may be loosened, and no proxy may silently replace the preregistered primary source.

## Official routes audited

1. B3 Search by trading session / daily bulletins:  
   https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/boletins-diarios/pesquisa-por-pregao/pesquisa-por-pregao/  
   Historical daily bulletins/files are available, including PriceReport-style and instrument files, but they do not satisfy the frozen raw per-event tape contract.

2. B3 Historical quotations:  
   https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/  
   Historical OHLC/summary data is useful for other protocols but cannot define the five preregistered tick-microstructure features.

3. B3 UP2DATA FAQ / historical products:  
   https://www.b3.com.br/en_us/market-data-and-indices/data-services/up2data/helpdesk/  
   B3 describes standardized market/reference products and directs users to authorized distributors for historical products not available on the public website.

4. B3 UP2DATA service:  
   https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/  
   Access is a contracted commercial path and therefore is outside the Factory's free-source autonomous route.

Public `TradeInformationConsolidated`-style daily products are also insufficient: they provide consolidated daily trade statistics rather than the raw event sequence required by v3.

## Scientific classification

`H2730-H2889 = FAIL_CLOSED_SOURCE_DATA_GAP`

This is **not** evidence against the microstructure mechanism and is **not** legitimate `VALID_RARITY_NO_THRESHOLD_CROSS`. The protocol remains frozen for future use if exact primary evidence becomes available under its original contract.

MT5 remains strictly `INDEPENDENT_SECONDARY_SOURCE / CROSS_VALIDATION_ONLY`; it cannot become ledger authority, replace B3 primary evidence, reconstruct the historical test, alter a prospective clock, or increment scientific counters.

## Continuation

Issue #293 opens a separate preregistration path for a materially distinct frontier based on free official cross-market observations (BCB/Tesouro/public B3 consolidated series where exact point-in-time semantics are auditable). It must be frozen before any economics and may not change the H2730-H2889 tick protocol.

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `NOT_APPROVED=true`
- `ENGINE_FEED=false`
- `ORDERS=0`
- `REAL_CAPITAL=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `NO_COUNTER_RESET=true`
- `FAIL_CLOSED=true`
- `H1_ECONOMICS_READ=false`
