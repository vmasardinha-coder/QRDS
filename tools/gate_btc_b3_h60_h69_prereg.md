# B3 H60-H69 Pre-registration

Status: RESEARCH ONLY — PRE-RESULT
Parent issue: #124

## Isolation and cutoff
H1 economics and every partial prospective survivor economics stream are forbidden inputs. Historical cutoff remains exclusive 2026-08-10 America/Sao_Paulo. Orders=0, real capital=0, engine_feed=false. H50-H59 is treated only as a closed-null/rejection ledger; no failed-cell recycling or parameter salvage is permitted.

## Transition of data dimension
This generation deliberately leaves OHLCV-only single/cross-WIN/WDO feature expansion and tests lagged cross-market/macro states. External data must be public, auditably sourced, timestamped, causal and reproducible. Every source gets URL/provider, raw hash or immutable version identifier where available, schema/timezone checks, date coverage and missingness report before economics. No forward fill across market holidays, no synthetic backfill, no future-close leakage.

Discovery B3 execution data remains exact-sync WIN/WDO 2024_26 M5. Independent replication remains 2020_22 + 2022_24 M15. External states are joined only using information known before the B3 session signal time. For US/global daily closes, use the most recent completed foreign session strictly before the B3 session open. For Brazilian daily macro/FX series, use only values whose publication timestamp is before the B3 session open; otherwise lag one additional business day.

## Source priority
1. Official/open sources first: Banco Central do Brasil/SGS or PTAX for BRL/monetary series, FRED for US rates/volatility when series publication timing is auditable, and exchange/index-provider public histories when legally accessible.
2. Stable public mirrors such as Stooq may be used only when provenance and date semantics are explicit and independently sanity-checked against a second public reference over an overlap sample.
3. If a family cannot meet provenance/coverage/timestamp rules with free/open data, mark that family DATA_GAP and continue the others. Do not substitute scraped or synthetic data silently.

## Frozen families
- H60 prior-day USD/BRL shock state: standardized absolute prior available BRL move versus trailing-20 available observations, thresholds 1.0/1.5. Trade WIN and WDO separately in same/opposite sign of BRL depreciation; hold 60/120m.
- H61 prior-day US equity risk state: prior completed S&P 500 or broad-US-equity return standardized by trailing-20 absolute return, thresholds 1.0/1.5. Trade WIN in same/opposite risk sign; WDO in opposite/same risk sign as distinct frozen alternatives; hold 60/120m.
- H62 prior-day volatility state: prior completed VIX change standardized by trailing-20 absolute change, thresholds 1.0/1.5. Rising-vol regime tests WIN short/WDO long and exact inverses; hold 60/120m.
- H63 prior-day US rates shock: prior completed 10Y yield change standardized by trailing-20 absolute change, thresholds 1.0/1.5. Test WIN and WDO same/opposite sign alternatives; hold 60/120m.
- H64 prior-day commodity state: use WTI and copper separately; standardized prior completed daily return thresholds 1.0/1.5. Test WIN/WDO same/opposite commodity sign with instrument identity frozen in parameter label; hold 60/120m.
- H65 cross-market confirmation/disagreement: combine prior US equity sign and USD/BRL sign. Four fixed states (risk-on BRL-strength, risk-off BRL-weakness, and two disagreements). Trade WIN/WDO using state-specific same/inverse mappings preregistered in the runner; hold 60/120m.
- H66 macro shock persistence: require the same external sign on two consecutive completed observations and second-day standardized magnitude >=0.75/1.0. Test continuation and reversal on WIN/WDO; hold 60/120m.
- H67 scheduled-calendar regime: pre-known weekday/month-turn/FOMC/Copom decision-day flags only from calendars known ex ante. Compare fixed directional continuation/fade mappings conditioned on current first-30m B3 sign; no post-event surprise values; hold 60/120m.
- H68 global risk composite: fixed equal-weight sign vote from prior US equity, VIX inverse sign, USD/BRL inverse sign and US10Y inverse sign. Require absolute vote >=2/3. Trade WIN with vote and inverse; WDO inverse vote and inverse-of-inverse as separate alternatives; hold 60/120m.
- H69 lagged cross-market residual: rolling-60 available-observation regression of WIN prior-session daily return on prior available USD/BRL + US equity states, fit using only earlier dates. If current lagged residual z-score abs >=1.5/2.0, test mean reversion and continuation in current WIN first-30m entry; hold 60/120m.

## Frozen gates
Same hard gates as H30-H59 per traded leg: minimum 60 trades; reference net edge >0.25 bp/trade; positive under stress cost; positive after one-extra-bar delayed entry; both long and short >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. A family survives discovery only with >=2 qualified cells and parameter/horizon breadth on at least one leg. Replication must independently satisfy the same family rule. Maximum 2 final survivors; no forced promotion.

## Data QA gate before economics
For every external series used by a family: >=90% eligible-session join coverage in discovery and replication after causal lagging; monotonic unique dates; no timestamps at/after B3 signal time; no more than 5 consecutive B3 sessions filled by stale external observation unless the external market itself was formally closed; explicit provider/source metadata; deterministic join. Any violation makes only the affected family DATA_GAP/REJECTED_DATA, not a reason to relax the rule.

## Transition rule
Discovery null -> reject family. Discovery survivor + replication failure -> reject failed replication. Replicated survivor -> freeze exact rule/version/source hashes and hand off to separate blind prospective ledger. No backfill, retune, reanchor or partial prospective feedback.
