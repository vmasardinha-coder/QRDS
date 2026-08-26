# B3 H130-H139 — preregistration

Parent issue: #210

This generation is frozen before any economic result and moves to Brazil sovereign cash-curve / real-vs-nominal rates using official Tesouro Nacional / Tesouro Transparente daily title rates.

## Source-first contract

Primary candidate: Tesouro Transparente open-data package `taxas-dos-titulos-ofertados-pelo-tesouro-direto`, CSV resource `796d2059-14e9-44e3-80c9-2d9e30b405c1`, ODbL. No economics until provider/resource identity, raw SHA-256, schema, date semantics, title identity, dedupe, coverage, node construction and causal lag pass.

Observed source fields expected from the official dataset: title type, maturity date, base date, morning purchase yield and morning prices. Derived features are never written back as observed.

Causal rule: only the most recent completed Tesouro `Data Base` strictly before the B3 signal session may condition that session. Same-day Tesouro morning quotes are forbidden. No synthetic interpolation or forward fill beyond the frozen stale limit.

## Deterministic curve nodes

Per completed source date, using only non-coupon exact title classes after schema QA:
- nominal2Y: `Tesouro Prefixado`, maturity closest to 2.0 years;
- nominal5Y: `Tesouro Prefixado`, closest to 5.0 years;
- nominal8Y: `Tesouro Prefixado`, closest to 8.0 years;
- real5Y: `Tesouro IPCA+`, closest to 5.0 years;
- real10Y: `Tesouro IPCA+`, closest to 10.0 years.

Tie-break: smallest absolute maturity-distance, then earlier maturity, then lexical title. Missing exact class means missing node; no coupon-bearing substitution.

## Frozen family budget

- H130 nominal slope shock `(nominal8Y-nominal2Y)` daily-change z on trailing-20 median absolute changes; thresholds 1.0/1.5; same/inverse mappings; holds 60/120m.
- H131 nominal curvature shock `2*nominal5Y-nominal2Y-nominal8Y`; same z grid and mappings.
- H132 real slope shock `(real10Y-real5Y)`; same z grid and mappings.
- H133 nominal5Y yield shock; z 1.0/1.5; risk-off/risk-on and exact inverse mappings.
- H134 real5Y yield shock; z 1.0/1.5; same/inverse mappings.
- H135 sovereign breakeven-proxy shock `nominal5Y-real5Y`; this is explicitly a cash-bond yield-difference proxy, not an inflation swap; z 1.0/1.5.
- H136 nominal-vs-real twist: four sign states crossing nominal-slope and real-slope changes; each leg abs z >=0.75/1.0; exact state mapping/inverse.
- H137 sovereign stress breadth: fixed vote over nominal5Y, real5Y, nominal slope and breakeven-proxy changes; require 3/4 or 4/4 active votes at abs z>=1.0.
- H138 two-session sovereign stress persistence: same sign twice; second-day standardized magnitude >=0.75/1.0; continuation/fade.
- H139 lagged sovereign-factor residual: rolling-60/120 causal regression of prior WIN daily return on lagged nominal5Y, real5Y and nominal-slope states; residual abs z 1.5/2.0; current first-30m continuation/mean-reversion.

All families test WIN/WDO only under the already-frozen response datasets, next-bar execution, one-extra-bar delay, reference/stress costs, side/calendar/concentration gates and independent replication. Family discovery requires >=2 qualified cells plus parameter/horizon breadth. Maximum 2 survivors; null valid.

## Hard invariants

Historical cutoff exclusive `2026-08-10` America/Sao_Paulo. Discovery remains 2024_26 M5; independent replication remains 2020_22 + 2022_24 M15. Require >=90% causal join coverage separately in discovery and replication for every family input. Missing coverage is DATA_GAP, not rejection.

H1 economics unread. Survivor partial prospective economics unread. No retune, no backfill, no synthetic data, no silent proxy substitution. `orders=0`, `capital=0`, `engine_feed=false`, `NOT_APPROVED`.
