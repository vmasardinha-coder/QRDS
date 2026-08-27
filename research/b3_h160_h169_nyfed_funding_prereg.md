# B3 H160-H169 — NY Fed USD funding / repo stress

Issue: #244

Status: PREREGISTERED_SOURCE_QA_ONLY / NO_ECONOMICS

Historical cutoff: exclusive 2026-08-10 America/Sao_Paulo.

Hard boundary: H1 partial economics unread; survivor partial prospective economics unread; RESEARCH_ONLY=true; SHADOW_ONLY=true; NOT_APPROVED=true; ORDERS=0; REAL_CAPITAL=0; ENGINE_FEED=false; NO_RETUNE; NO_SYNTHETIC_BACKFILL.

## Economic distinction

H160-H169 tests lagged U.S. dollar secured/unsecured funding-market stress from Federal Reserve Bank of New York administered reference rates. It does not repackage Focus survey revisions (H150-H159), PTAX fixing microstructure (H140-H149), Brazilian sovereign cash-curve (H130-H139), B3 trades/activity (H120-H129), Cboe volatility or CFTC positioning.

## Frozen families

H160 SOFR-EFFR spread shock: secured-minus-unsecured daily rate spread; trailing-60 robust standardization; abs z 1.0/1.5; WDO stress same/inverse and WIN risk-off/inverse mappings; 60/120m holds.

H161 BGCR-TGCR spread shock: broad-vs-triparty collateral rate spread; trailing-60 robust standardization; abs z 1.0/1.5; WIN/WDO stress/inverse mappings; 60/120m holds.

H162 OBFR-EFFR spread shock: broader bank-funding minus fed-funds spread; trailing-60 robust standardization; abs z 1.0/1.5; WDO same/inverse and WIN inverse/same; 60/120m holds.

H163 SOFR volume shock: daily published SOFR volume change; trailing-20 absolute-change standardization; abs z 1.0/1.5; stress/inverse mappings; 60/120m holds.

H164 EFFR volume shock: same fixed construction for EFFR volume; abs z 1.0/1.5; stress/inverse mappings; 60/120m holds.

H165 SOFR distribution-width shock: official 99th-minus-1st percentile width change; trailing-20 standardization; abs z 1.0/1.5; WIN/WDO stress/inverse mappings; 60/120m holds.

H166 EFFR distribution-width shock: same fixed construction for EFFR; abs z 1.0/1.5; WIN/WDO stress/inverse mappings; 60/120m holds.

H167 secured/unsecured volume-ratio shock: SOFR volume divided by EFFR volume, log-change trailing-20 standardized; abs z 1.0/1.5; WDO same/inverse and WIN inverse/same; 60/120m holds.

H168 USD funding-stress breadth: fixed H160/H161/H162 votes; require 2/3 or 3/3 aligned votes at abs z >=1.0; WIN/WDO stress/inverse mappings; 60/120m holds.

H169 causal funding residual: rolling-60/120 fit of prior completed WIN/WDO daily return on lagged H160/H161/H162 spread states and H163/H164 volume shocks, using only earlier causally available rows; residual abs z 1.5/2.0; current first-30m continuation/mean-reversion; 60/120m holds.

## Official source contract before economics

Provider: Federal Reserve Bank of New York. Official Markets Data API, administered reference rates. Candidate exact stable JSON resources: `/api/rates/secured/sofr/search.json`, `/api/rates/secured/bgcr/search.json`, `/api/rates/secured/tgcr/search.json`, `/api/rates/unsecured/effr/search.json`, `/api/rates/unsecured/obfr/search.json`; no authentication.

Source QA must persist exact request URLs, response-byte SHA-256, schema and required field names, effective-date semantics, rate identity, percentile identity, volume units, duplicates, missingness, coverage for discovery and both replication blocks, and observed-vs-derived mapping. No scraping when the API is available.

Causality is conservative by preregistration: even though NY Fed reference rates are published on business mornings, B3 session D may condition only on the latest NY Fed observation available by the prior completed B3 session P. No same-session publication-time dependency, interpolation, forward-fill, synthetic reconstruction or silent proxying.

## Frozen scientific gates

Discovery 2024_26 M5. Independent replication 2020_22 + 2022_24 M15. Per-input causal join coverage >=90% separately in discovery and replication before economics. Per traded leg preserve existing hard gates: >=60 trades; reference net edge >0.25 bp/trade; positive stress-cost result; positive one-extra-bar delay; long and short each >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. Family survivor requires >=2 qualified cells plus parameter/horizon breadth; independent replication must satisfy the same family rule. Maximum 2 survivors; null valid.

No economics may execute from this file or its source-QA workflow.