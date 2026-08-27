# B3 H150-H159 — BCB Focus expectations revisions

Issue: #228

Status: PREREGISTERED_SOURCE_QA_ONLY / NO_ECONOMICS

Historical cutoff: exclusive 2026-08-10 America/Sao_Paulo.

Hard boundary: H1 partial economics unread; survivor partial prospective economics unread; RESEARCH_ONLY=true; SHADOW_ONLY=true; NOT_APPROVED=true; ORDERS=0; REAL_CAPITAL=0; ENGINE_FEED=false; NO_RETUNE; NO_BACKFILL.

## Economic distinction

H150-H159 tests lagged survey-expectation revisions/dispersion from the official BCB Sistema Expectativas de Mercado (Focus). It does not reuse PTAX fixing microstructure (H140-H149), sovereign curve (H130-H139), B3 trades/activity (H120-H129), Cboe volatility or CFTC positioning as renamed hypotheses.

## Frozen families

H150 Selic annual-median revision shock: trailing-20 absolute-revision standardized thresholds 1.0/1.5; WIN/WDO same and inverse mappings; 60/120m holds.

H151 IPCA annual-median revision shock: thresholds 1.0/1.5; WIN risk-on/risk-off and WDO inflation-risk same/inverse mappings; 60/120m holds.

H152 USD/BRL annual-median expectation revision shock: thresholds 1.0/1.5; WDO same/inverse and WIN inverse/same; 60/120m holds.

H153 GDP annual-median expectation revision shock: thresholds 1.0/1.5; WIN same/inverse and WDO inverse/same; 60/120m holds.

H154 Selic dispersion revision: official DesvioPadrao preferred; if absent, exact official Maximo-Minimo only after source schema confirms both fields before economics; thresholds 1.0/1.5; stress/inverse mappings; 60/120m holds.

H155 IPCA dispersion revision: same fixed construction and grid as H154.

H156 four-vote revision breadth: Selic/IPCA/FX/GDP standardized revisions; 3/4 or 4/4 aligned votes at abs z >=1.0; WIN/WDO vote/inverse mappings; 60/120m holds.

H157 expected-real-rate revision: same fixed annual horizon Selic median minus IPCA median, both observed inputs preserved; trailing-20 standardized change, thresholds 1.0/1.5; WIN/WDO same/inverse; 60/120m holds.

H158 Focus FX-vs-PTAX expectation-gap revision: latest causally available annual FX median minus prior completed official PTAX close under frozen H140 source contract; thresholds 1.0/1.5; WDO convergence/divergence and WIN inverse mappings; 60/120m holds.

H159 causal Focus residual: rolling 60/120 fit using only earlier causally available standardized Selic/IPCA/FX/GDP revisions; residual abs z 1.5/2.0; current first-30m continuation/mean-reversion; 60/120m holds.

## Source contract before economics

Provider: Banco Central do Brasil / Dstat. Dataset: Expectativas de Mercado. Official service: Olinda Expectativas v1 OData. License: ODbL per BCB Open Data catalog.

Source QA must persist provider/resource identity, exact request manifest, response-byte SHA-256, schema, indicator identity, annual horizon identity, date/reference-date semantics, duplicates, missingness, coverage for discovery and both replication blocks, and observed-vs-derived fields.

Causality: only observations provably available before the B3 signal decision may condition a session. If publication-time semantics are not exact enough, use one complete B3-session lag. No interpolation, forward fill, synthetic reconstruction, silent proxying or result-driven horizon choice.

## Frozen scientific gates

Discovery 2024_26 M5. Independent replication 2020_22 + 2022_24 M15. Per-input causal join coverage >=90% separately in discovery and replication. Per traded leg: >=60 trades; reference net edge >0.25 bp/trade; stress-cost >0; one-extra-bar delay >0; long and short each >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. Family survivor: >=2 qualified cells plus parameter/horizon breadth; independent replication must independently satisfy the same family rule. Maximum 2 survivors; null valid.

No economics may execute from this file or its source-QA workflow.