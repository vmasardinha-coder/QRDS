# B3 H70-H79 Pre-registration

Status: RESEARCH ONLY — PRE-RESULT
Parent issue: #163

## Isolation and cutoff
H1 economics and all partial prospective survivor economics are forbidden inputs. Historical cutoff is exclusive 2026-08-10 America/Sao_Paulo. Orders=0, real capital=0, engine_feed=false, NOT_APPROVED. H60-H69 terminal states are a permanent rejection/data-gap ledger; rejected cells are not recycled and blocked SP500/H61 inputs are excluded.

## Data dimension
This generation tests rates-curve shape, implied-volatility level/term structure, joint macro states, non-equity shock breadth/dispersion and a causal non-equity residual. Observed sources and derived features are separate. Official sources are preferred: Banco Central do Brasil USD/BRL, Cboe VIX/VIX9D, U.S. Treasury daily par yield curve, EIA WTI. Every observed series requires provider/URL/raw hash, schema, unique monotonic dates, causal lag, timezone/date semantics and >=90% eligible-session join coverage in discovery and replication before economics. No synthetic backfill or silent substitution.

Discovery execution data remains exact-sync WIN/WDO 2024_26 M5. Independent replication remains 2020_22 + 2022_24 M15. External daily observations must be completed and known strictly before the B3 session signal time.

## Frozen family budget
- H70 Treasury curve-slope shock: prior completed (10Y-2Y) slope daily change / trailing-20 median absolute slope change; thresholds 1.0/1.5; WIN/WDO same/opposite; hold 60/120m.
- H71 curve-slope persistence: two consecutive same-sign slope changes; second-day standardized magnitude >=0.75/1.0; WIN/WDO continuation/reversal; hold 60/120m.
- H72 VIX level regime: prior completed VIX rolling-60 causal percentile bands 20/80 and 30/70; condition current first-30m B3 sign; continuation/fade on WIN/WDO; hold 60/120m.
- H73 volatility term structure: prior completed VIX9D/VIX ratio. Fixed coarse ratio states <=0.90 or >=1.10 plus causal rolling log-ratio z abs >=1.0/1.5 as distinct preregistered labels; risk-on/risk-off and exact inverse mappings on WIN/WDO; hold 60/120m. Official VIX9D failure => H73 DATA_GAP only.
- H74 Treasury parallel-vs-twist: joint prior 2Y/10Y changes; states both-up, both-down, 2Y-up/10Y-down, 2Y-down/10Y-up; each leg abs standardized move >=0.75/1.0; state-specific same/inverse WIN/WDO; hold 60/120m.
- H75 FX x curve confirmation/disagreement: prior USD/BRL sign x prior slope-change sign, four fixed states; same/inverse WIN/WDO; hold 60/120m.
- H76 WTI x curve confirmation/disagreement: prior WTI-return sign x prior slope-change sign, four fixed states; same/inverse WIN/WDO; hold 60/120m.
- H77 non-equity shock breadth: standardized prior USD/BRL, VIX-change, WTI-return and slope-change; component abs threshold 1.0; breadth >=2/4 or >=3/4; fixed signed risk vote with VIX sign inverted; WIN vote/inverse and WDO inverse-vote/vote; hold 60/120m.
- H78 signed cross-market dispersion: same four fixed risk-signed inputs; causal cross-sectional dispersion >=1.0/1.5 x trailing-60 median dispersion; condition current first-30m B3 sign and test continuation/fade on WIN/WDO; hold 60/120m.
- H79 non-equity lagged residual: rolling causal regression windows 60/120 observations of prior WIN daily return on lagged USD/BRL, VIX, WTI and Treasury slope states, fit only on earlier dates; residual z abs >=1.5/2.0; mean-reversion/continuation on current WIN first-30m sign; hold 60/120m.

## Frozen gates
Per traded leg: minimum 60 trades; reference net edge >0.25 bp/trade; positive under frozen stress cost; positive after one-extra-bar delayed entry; both long and short >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%. A family survives discovery only with >=2 qualified cells and parameter/horizon breadth on at least one leg. Independent older-block replication must independently satisfy the same family rule. Maximum 2 final survivors; null result valid.

## Transition
DATA_GAP stays DATA_GAP and does not weaken provenance. Discovery null -> reject. Discovery survivor + replication failure -> reject failed replication. Replicated survivor -> freeze exact rule/version/source hashes and hand off to a separate blind prospective ledger, with no backfill, retune, reanchor or partial-result feedback.
