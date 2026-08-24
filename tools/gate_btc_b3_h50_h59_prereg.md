# B3 H50-H59 Pre-registration

Status: RESEARCH ONLY — PRE-RESULT
Parent issue: #119

## Isolation
H1 economics and every prospective partial survivor economics stream are forbidden inputs. Historical cutoff remains exclusive 2026-08-10 America/Sao_Paulo. Orders=0, real capital=0, engine_feed=false. H40-H49 is treated only as a closed null generation; no failed-cell cherry-picking is permitted.

## Data and replication
Use the same pinned community WIN/WDO Profit continuous source and exact synchronization contract as H30-H49. Discovery uses 2024_26 M5. Independent replication uses 2020_22 + 2022_24 M15. No forward fill. Sessions must start 09:00 with no internal bar gaps. Only scale-invariant causal features are allowed.

## Frozen families
- H50 path-efficiency state: first-60m efficiency ratio = abs(close-open)/sum(abs(bar-to-bar close changes)). Compare to trailing-20 session median. Test unusually efficient path >=1.25/1.50x median and unusually inefficient path <=0.75/0.60x median. Trade own 60m sign and inverse as fixed alternatives; hold 60/120m.
- H51 realized-semivariance imbalance: first-60m positive-return semivariance versus negative-return semivariance. If dominant/minor ratio >=1.5/2.0, trade dominant sign and inverse; hold 60/120m.
- H52 cross-asset path-efficiency divergence: abs(ER_WIN-ER_WDO) >=0.20/0.35 at 60m. Trade the less-efficient leg in the more-efficient leg's 60m sign and inverse; hold 60/120m.
- H53 drawdown/recovery state: first-60m maximum excursion from session open reaches >=1.25/1.50x trailing-20 median absolute 60m move and the close recovers at least 50%/75% from the extreme. Trade recovery direction and inverse; hold 60/120m.
- H54 compression-break state: first-30m range <=0.60/0.80x trailing-20 median first-30m range, followed during minutes 30-60 by a break of the first-30m high or low. Trade break direction and fade as separate alternatives; hold 60/120m.
- H55 asynchronous cross-asset shock: at 60m one asset has abs(return)>=1.25/1.50x its trailing-20 median absolute 60m return while the other remains <=0.60x its own scale. Trade the quiet leg toward leader sign and inverse; hold 60/120m.
- H56 price/volume disagreement: first-60m price-return sign disagrees with signed-volume-proxy sign. Require both abs(return)/trailing scale and abs(signed-volume)/trailing scale >=1.0/1.5. Trade price sign and volume sign as distinct alternatives; hold 60/120m.
- H57 short-horizon autocorrelation state: lag-1 autocorrelation of first-60m bar returns has abs(value)>=0.25/0.40. For positive autocorrelation trade own 60m sign and inverse; for negative autocorrelation trade fade of own 60m sign and inverse; hold 60/120m.
- H58 wick-pressure imbalance: aggregate upper-wick minus lower-wick pressure over first 30m, normalized by aggregate bar range, has abs(value)>=0.20/0.35. Trade pressure direction and inverse; hold 60/120m.
- H59 prior-session trend interaction: prior-session return magnitude >=1.0/1.5x trailing-20 median absolute session return. At current first 30m, classify same-sign/opposite-sign opening response. Trade prior-session sign and current 30m sign as separate frozen alternatives; hold 60/120m.

## Gates
Same hard gates as H30-H49 per traded leg: minimum 60 trades; reference net edge >0.25 bp/trade; positive under stress cost; positive after one-extra-bar delayed entry; both long and short >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. A family survives discovery only with >=2 qualified cells and parameter/horizon breadth on at least one leg. Replication must independently satisfy the same family rule. Maximum 2 final survivors; no forced promotion.

## Transition rule
Discovery null -> reject family. Discovery survivor + replication failure -> reject failed replication. Replicated survivor -> freeze exact rule/version/source hashes and hand off to a separate blind prospective ledger. No backfill, no retune, no reanchor, no partial prospective feedback.
