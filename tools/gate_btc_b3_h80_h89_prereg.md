# B3 H80-H89 preregistration

Status: RESEARCH_ONLY — PRE-RESULT
Parent issue: #167
Cutoff: exclusive 2026-08-10 America/Sao_Paulo.

H80-H89 are frozen exactly as specified in issue #167: WDO calendar carry, IND/WIN calendar spread, DI curve slope, WDO futures-vs-spot basis, roll-window compression, settlement-vs-close dislocation, OI/volume state, front/next liquidity migration, cross-market carry breadth, and a causal B3-native residual. Directions, thresholds and 60/120m holds are fixed before results.

Scientific gates remain identical to H30-H79: >=60 trades per eligible cell; reference net edge >0.25 bp/trade; positive at stress cost and one-extra-bar delayed entry; both long and short >=15 and positive; >=2 eligible half-year buckets with >=15 and positive; top-5 positive contribution <=40%; discovery family breadth requires >=2 qualified cells plus parameter/horizon breadth; independent older-block replication must satisfy the same family rule. Maximum 2 survivors; null valid.

Data gate precedes economics. Official B3/BCB/open auditable sources only, with provider/URL/hash or immutable version, schema/date/timezone semantics, dedupe, causal availability and coverage checks. Observed data and derived features are separate. No synthetic backfill, no fabricated settlement/OI/volume. A missing dimension becomes DATA_GAP only for dependent families; other dimensions continue.

H1 economics and survivor partial economics are forbidden inputs. orders=0, capital=0, engine_feed=false, NOT_APPROVED.
