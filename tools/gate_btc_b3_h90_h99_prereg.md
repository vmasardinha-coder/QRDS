# B3 H90-H99 Pre-registration

Parent issue: #180
Status: RESEARCH_ONLY / PRE-RESULT

## Hard isolation
Historical cutoff is exclusive 2026-08-10 America/Sao_Paulo. H1 economics and all survivor partial prospective economics are forbidden inputs. orders=0, real_capital=0, engine_feed=false, NOT_APPROVED=true. No retune, synthetic backfill, or reuse of H80-H89 B3 futures-structure fields.

## Frozen family budget
- H90 HY OAS shock: trailing-20 absolute-change standardization; thresholds 1.0/1.5; WIN/WDO same/opposite stress mapping; hold 60/120m.
- H91 IG OAS shock: same grid and mappings.
- H92 HY OAS level regime: rolling-60 causal percentiles 20/80 and 30/70; condition current first-30m sign; continuation/fade; WIN/WDO; hold 60/120m.
- H93 10Y real-yield shock: trailing-20 abs-change z 1.0/1.5; same/opposite on WIN/WDO; hold 60/120m.
- H94 10Y breakeven shock: trailing-20 abs-change z 1.0/1.5; same/opposite on WIN/WDO; hold 60/120m.
- H95 broad trade-weighted USD shock: prior completed return, trailing-20 abs-return z 1.0/1.5; same/opposite dollar-stress mapping; hold 60/120m.
- H96 SOFR-EFFR spread shock: prior completed spread change, trailing-20 abs-change z 1.0/1.5; continuation/reversal WIN/WDO; hold 60/120m.
- H97 HY credit x real-yield joint state: each leg abs z >=0.75/1.0; four sign states; same/inverse mappings; hold 60/120m.
- H98 stress breadth: HY OAS, IG OAS, broad USD, SOFR-EFFR; abs z>=1.0; require 2/4 or 3/4; fixed stress vote/inverse; hold 60/120m.
- H99 causal residual: rolling 60/120 fit of prior WIN daily return on lagged HY OAS, 10Y real yield, broad USD; residual abs z 1.5/2.0; current WIN first-30m continuation/mean reversion; hold 60/120m.

## Source gate
Candidate observed series: BAMLH0A0HYM2, BAMLC0A0CM, DFII10, T10YIE, DTWEXBGS, SOFR, DFF via public Federal Reserve/FRED-compatible CSV endpoints. Every series must pass provider/URL/raw SHA-256/schema/date uniqueness/coverage/missingness checks. Use at least one full-session lag before B3 signal time. No forward fill across unpublished observations.

## Frozen scientific gates
Per traded leg: >=60 trades; reference net edge >0.25 bp/trade; positive under frozen stress cost; positive one-extra-bar delayed entry; both long and short >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. Family discovery survivor requires >=2 qualified cells plus parameter/horizon breadth. Independent replication on 2020_22 + 2022_24 must satisfy the same family rule. Max 2 survivors; null valid.
