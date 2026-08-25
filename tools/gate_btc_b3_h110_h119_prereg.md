# B3 H110-H119 Pre-registration

Status: RESEARCH ONLY — PRE-RESULT
Parent issue: #199
Historical cutoff: exclusive 2026-08-10 America/Sao_Paulo

This generation tests lagged official Cboe implied-volatility term/relative-volatility states. It is economically distinct from H62 single-VIX-change, prior OHLCV/cross-market/macro generations, B3 futures-structure, and CFTC positioning. H1 economics and all partial survivor prospective economics are forbidden inputs. Orders=0, real capital=0, engine_feed=false, NOT_APPROVED.

## Frozen families and coarse grids
- H110 VIX9D/VIX term inversion: prior completed US-session ratio; levels >=1.00/1.10 and <=0.90/0.85; WIN de-risk/risk-seeking, WDO defensive/inverse; holds 60/120m.
- H111 VVIX/VIX vol-of-vol ratio shock: one-session log-ratio change, trailing-60 causal median absolute change scale; abs z 1.0/1.5; stress and exact inverse mappings on WIN/WDO; holds 60/120m.
- H112 OVX/VIX oil-vs-equity relative-vol shock: one-session log-ratio change; same z 1.0/1.5; same/inverse mappings; holds 60/120m.
- H113 GVZ/VIX gold-vs-equity relative-vol shock: same z 1.0/1.5; same/inverse mappings; holds 60/120m.
- H114 VXEEM/VIX EM-vs-US relative-vol shock: same z 1.0/1.5; same/inverse mappings; holds 60/120m.
- H115 cross-vol confirmation: sign vote from prior completed changes in VIX9D, VVIX, OVX, GVZ, VXEEM; require 3/5 or 4/5 aligned stress/calm votes; WIN de-risk/inverse and WDO defensive/inverse; holds 60/120m.
- H116 term inversion + vol-of-vol confirmation: VIX9D/VIX >=1.00/1.10 and positive VVIX/VIX change z >=1.0/1.5; exact stress and exact inverse mappings; holds 60/120m.
- H117 cross-vol dispersion: cross-sectional standard deviation of causally standardized prior levels VIX, OVX, GVZ, VXEEM; trailing-60 dispersion-change z 1.0/1.5; continuation/fade on WIN/WDO; holds 60/120m.
- H118 two-session stress persistence: same stress sign on two consecutive completed observations and second-day standardized magnitude >=0.75/1.0; continuation/fade on WIN/WDO; holds 60/120m.
- H119 lagged vol-complex residual: rolling-60 causal regression of prior-session WIN intraday return (first synchronized session open to last synchronized session close; no overnight return or roll inference) on lagged VIX9D/VIX, VVIX/VIX and VXEEM/VIX states, fit only on earlier observations; residual abs z 1.5/2.0; current WIN first-30m continuation/mean-reversion; holds 60/120m.

## Source QA before economics
Official Cboe public historical-index CSV surfaces only for VIX, VIX9D, VVIX, OVX, GVZ and VXEEM. Every observed source records provider, URL, raw SHA-256, schema, US date semantics, first/last date, missingness and duplicate checks. Derived ratios/z-scores/dispersion are deterministic transforms of observed closes and are separately hashable.

For every family, join only the most recent completed Cboe observation strictly before the B3 session signal. No future-close leakage, no synthetic backfill, no silent proxy substitution. Reject stale observations older than 5 calendar days unless a later market-calendar exception is explicitly proven. Require >=90% eligible-session join coverage in both discovery and independent replication; a failure marks only affected families DATA_GAP.

## Frozen scientific gates
Per traded leg: >=60 trades; reference net edge >0.25 bp/trade; positive stress-cost result; positive with one-extra-bar delayed entry; long and short each >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. Discovery survivor requires >=2 qualified cells plus parameter/horizon breadth. Independent replication uses 2020_22 + 2022_24 and must satisfy the same family rule. Maximum 2 final survivors. Null result is valid. No retune, backfill, rejected-family recycling or partial-holdout feedback.
