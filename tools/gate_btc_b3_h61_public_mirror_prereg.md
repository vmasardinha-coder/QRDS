# B3 H61 public-mirror source recovery preregistration

Parent: #124 / #157
Status: PRE-RESULT, RESEARCH_ONLY

This recovery changes only source delivery/provenance for the already-frozen H61 US-equity dimension. It does not change the H61 economic hypothesis, grids, mappings, costs or gates.

## Frozen source contract
Primary observed series: Stooq daily cash S&P 500 index `^SPX`, direct CSV history. Capture request URL, raw SHA-256, parser/schema version, unique monotonic dates, row count, first/last dates, and identity as a cash price index. Keep only observations dated before the exclusive historical cutoff 2026-08-10.

Independent public sanity reference: Yahoo Finance daily `^GSPC` chart history over the same period. Capture request URL/response SHA-256 and align by calendar date. Require at least 250 overlapping daily closes, >=99% sign agreement of non-zero daily returns, and median absolute relative close difference <=0.25%. If this sanity reference cannot be fetched or these checks fail, H61 remains DATA_GAP and no economics run.

For B3 session joins, use the latest completed US cash-index observation strictly before the B3 session date (`allow_exact_matches=false`). Require >=90% join coverage in discovery and independent replication and no joined observation older than 5 calendar days. No forward fill beyond this merge rule and no synthetic backfill.

## Frozen H61 economics
Signal: prior completed S&P 500 daily return divided by trailing-20 median absolute daily return, with the scale using only earlier observations.
Thresholds: {1.0, 1.5}.
Traded legs: {WIN, WDO}.
Mappings: {same sign, opposite sign}.
Holding horizons: {60m, 120m}.
Execution/costs: unchanged H30-H69 frozen costs, next-bar entry, one-extra-bar delayed-entry stress.
Hard gates: unchanged minimum 60 trades, positive reference net edge >0.25 bp/trade, positive stress cost, positive delayed entry, both sides >=15 and positive, >=2 eligible half-year/calendar buckets with >=15 and positive, top-5 contribution <=40%, >=2 qualified cells with parameter/horizon breadth, then independent older-block replication under the same rule. Maximum survivor policy unchanged.

Cutoff exclusive 2026-08-10 America/Sao_Paulo. H1 economics and all partial prospective survivor economics are forbidden inputs. orders=0, capital=0, engine_feed=false. Null result is valid.

If H61 becomes DATA_READY, H65/H68/H69 remain separate frozen families and must be executed only under their original preregistration; H61 results cannot be used to alter their mappings/grids.