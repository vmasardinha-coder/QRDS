# B3 H180-H189 — U.S. Treasury nominal/real curve stress preregistration

Frozen before any H180-H189 economics. Supersedes the later Treasury draft in issue #260 only because H170-H179 identifiers had already been frozen by autonomous commit `fa6ea8a224e647d00e4611b14df33b2c184d0ab3`. No H170-H179 economics were consulted for this renumbering.

Historical research cutoff is exclusive `2026-08-10` in America/Sao_Paulo. H1 partial economics remain unread until the original 20/20 unlock. Survivor prospective partial economics are not research feedback.

## Source contract

Primary source is the U.S. Department of the Treasury official Daily Treasury Par Yield Curve Rates and Daily Treasury Par Real Yield Curve Rates stable XML/download endpoints. Ingestion must persist request URL, raw SHA-256, response metadata, schema/tenor identity, observation-date semantics, coverage, missingness, duplicates, observed-vs-derived classification and a causal availability policy. No tenor or provider proxy substitution. If publication time cannot be proven, impose one full completed B3-session lag.

## Families

- H180: nominal 2s10s slope daily-change robust-z(60), |z| 1.0/1.5, WIN risk-on/risk-off and WDO stress/inverse, hold 60/120m.
- H181: nominal 3m10y slope daily-change robust-z(60), |z| 1.0/1.5, WIN/WDO same+inverse, hold 60/120m.
- H182: nominal 10Y level daily-change standardized(20), |z| 1.0/1.5, WIN inverse/same and WDO same/inverse, hold 60/120m.
- H183: nominal 2Y level daily-change standardized(20), same grid/directions, hold 60/120m.
- H184: real 10Y level daily-change standardized(20), |z| 1.0/1.5, WIN inverse/same and WDO same/inverse, hold 60/120m.
- H185: real 5s10s slope daily-change robust-z(60), |z| 1.0/1.5, WIN/WDO stress/inverse, hold 60/120m.
- H186: DERIVED nominal 10Y minus real 10Y spread daily-change standardized(20), only after both exact rows are causal; |z| 1.0/1.5, WIN inflation/risk and WDO same/inverse, hold 60/120m.
- H187: curve-stress breadth from fixed H180/H181/H182/H184 votes; 3/4 or 4/4 at |z|>=1.0, WIN/WDO stress+inverse, hold 60/120m.
- H188: nominal-real divergence, standardized nominal 10Y change minus standardized real 10Y change, |z| 1.0/1.5, WIN/WDO same+inverse, hold 60/120m.
- H189: causal rolling residual using only earlier available rows, windows 60/120, residual |z| 1.5/2.0, first-30m continuation/mean-reversion, hold 60/120m.

## Frozen gates

Discovery `2024_26` M5. Independent replication `2020_22 + 2022_24` M15 on existing frozen B3 response datasets. Required causal join coverage >=90% independently in discovery and replication. Preserve frozen costs, next-bar plus one-extra-bar execution delay, >=60 trades, reference net edge >0.25 bp/trade, positive stress-cost result, long/short each >=15 and positive, >=2 positive eligible half-year buckets each >=15, top-5 positive contribution <=40%, parameter/horizon breadth and independent replication. Maximum two survivors; null is valid.

If exact real-yield coverage fails, only H184-H186/H188-H189 may be DATA_GAP; independent nominal families continue without proxy substitution.

`RESEARCH_ONLY=true`
`SHADOW_ONLY=true`
`NOT_APPROVED=true`
`ORDERS=0`
`REAL_CAPITAL=0`
`ENGINE_FEED=false`
`NO_RETUNE=true`
`NO_SYNTHETIC_BACKFILL=true`
