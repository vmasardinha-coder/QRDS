# B3 H100-H109 Pre-registration

Status: RESEARCH ONLY — PRE-RESULT
Parent issue: #191
Historical cutoff: exclusive 2026-08-10 America/Sao_Paulo

This generation tests lagged official CFTC positioning/crowding states and is intentionally distinct from prior OHLCV, cross-market price, B3 futures-structure and macro-level generations. H1 economics and partial prospective survivor economics are forbidden inputs. Orders=0, real capital=0, engine_feed=false, NOT_APPROVED.

## Frozen families
- H100 E-mini S&P positioning extreme: normalized net leveraged/spec positioning over OI; causal rolling 104-week percentile bands 10/90, 20/80; WIN continuation/fade, WDO inverse/same; holds 60/120m.
- H101 US Dollar Index positioning extreme: normalized net spec positioning/OI; percentile bands 10/90, 20/80; WDO same/opposite crowded-dollar sign, WIN inverse/same; holds 60/120m.
- H102 US 10Y Treasury positioning extreme: normalized net leveraged/spec positioning/OI; percentile bands 10/90, 20/80; WIN/WDO same/opposite duration-risk mappings; holds 60/120m.
- H103 WTI positioning extreme: normalized net money-manager/spec positioning/OI; percentile bands 10/90, 20/80; WIN/WDO same/opposite commodity-risk mappings; holds 60/120m.
- H104 copper positioning extreme: normalized net managed-money/spec positioning/OI; percentile bands 10/90, 20/80; WIN/WDO same/opposite global-growth mappings; holds 60/120m.
- H105 weekly positioning impulse: one-report change in normalized positioning, trailing-52 causal abs-change standardization, abs z 1.0/1.5; fixed same/inverse mappings; holds 60/120m.
- H106 cross-market crowding confirmation: fixed sign vote across equity, USD, 10Y, WTI, copper; require 3/5 or 4/5; WIN with/inverse vote, WDO inverse/same; holds 60/120m.
- H107 positioning divergence: prior completed weekly price direction versus positioning impulse sign; four fixed states, abs positioning z 1.0/1.5; continuation/fade; holds 60/120m.
- H108 crowding breadth: number of markets beyond causal 20/80 or 10/90 positioning percentiles; thresholds >=2/>=3; fixed de-risk/risk-seeking mappings; holds 60/120m.
- H109 lagged positioning residual: rolling 104-week causal regression of prior WIN weekly return on lagged equity/USD/10Y positioning, fit only on earlier published reports; residual abs z 1.5/2.0; current WIN first-30m continuation/mean-reversion; holds 60/120m.

## Source contract before economics
Official CFTC Historical Compressed files only. Financial futures families use Traders in Financial Futures futures-only yearly text archives. Commodity families use Disaggregated futures-only yearly text archives. Record report as-of date and publication availability separately; no report may affect a B3 session unless its publication timestamp is strictly before session open. Record URL, raw SHA-256, archive member, schema, contract market code/name, date coverage, missingness, duplicate checks, OI denominator and deterministic derived-series hash. No synthetic backfill and no silent contract substitution. Taxonomy or identity ambiguity fails only the affected family closed as DATA_GAP.

## Frozen scientific gates
Per traded leg: >=60 trades; reference net edge >0.25 bp/trade; positive stress-cost result; positive with one-extra-bar delayed entry; long and short each >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. Discovery survivor requires >=2 qualified cells plus parameter/horizon breadth. Independent replication uses frozen older blocks 2020_22 + 2022_24 and must satisfy the same family rule. Maximum 2 final survivors; null result valid. No retune, backfill or partial-holdout feedback.