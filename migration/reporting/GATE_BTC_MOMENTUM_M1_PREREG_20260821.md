# GATE BTC Momentum M1 Preregister — 2026-08-21

## Purpose
Independent shadow regime challenger inspired by an external contemporaneous momentum snapshot. This study is diagnostic only and must not feed Delta, QOS, V16, Profit Preservation or any allocation engine.

## Discovery boundary
The 2026-08-16 to 2026-08-19 interval was used only to form the initial hypothesis. It is RETROSPECTIVE_DISCOVERY_ONLY and cannot be counted as prospective validation.

Initial conclusion frozen at preregistration: approximately 30-day momentum best represented the observed structural state, while approximately 14-day momentum appeared to contain faster information about score movement. The hypothesis to test prospectively is that breadth, breadth change and distance of negative scores to zero may identify cross-sectional regime expansion.

## Frozen formula
- R14 = P_t / P_(t-14) - 1
- R30 = P_t / P_(t-30) - 1
- Impulse = R14 - R30
- All Z values are cross-sectional population z-scores at the same cutoff.
- M0A = Z(R30)
- M0B = 0.70 * Z(R30) + 0.30 * Z(R14)
- M1 = 0.65 * Z(R30) + 0.25 * Z(R14) + 0.10 * Z(Impulse)
- DisplayScore = clip(M1, -0.8, +0.8); clipping is display-only and never changes ranking.

No weights may be changed because of future Empiricus snapshots, Delta performance/ranking, or future returns.

## Frozen regime diagnostics
- breadth_pct_m1_gt_zero
- delta_breadth_pct_points
- median_m1
- cross_sectional_dispersion_m1
- negative_median_distance_to_zero

No bullish/bearish threshold is frozen at preregistration. Threshold discovery from the 16-19 August episode is prohibited.

## External comparisons
External Empiricus snapshots are benchmark/audit evidence only. They may be used for rank/scale diagnostics after M1 has been calculated for the same cutoff, but never as a tuning target.

Delta comparison is valid only when a same-cutoff common-universe score/rank exists. The diagnostic metric is Spearman rank correlation. A high correlation would suggest similar cross-sectional information; a low correlation with similar regime performance would suggest different selectors exposed to the same regime.

Macro Quant is an intended independent replica using the exact same frozen formulas. A mismatch is an implementation/provenance issue, not permission to retune.

## Prospective boundary
Freeze date: 2026-08-21.
The first eligible calculation may use only fully closed evidence available through the 2026-08-20 close. Subsequent rows must be append-only and causal.

## Reporting
- Collection: clock, provenance, universe size and GREEN/AMBER/RED only.
- Master: full ranking, M0A/M0B/M1, breadth, breadth change, median, dispersion, negative distance and valid external/Delta comparisons.
- Executive: only material regime changes or new conclusions.
- Profit Preservation: excluded.
- Allocation Engine: excluded; weight zero.

## Safety
RESEARCH_ONLY=true
SHADOW_ONLY=true
NOT_APPROVED=true
ENGINE_FEED=false
PROMOTION_ELIGIBLE=false
ALLOCATION_WEIGHT=0
ORDERS=0
REAL_CAPITAL=0
AUTOMATIC_TUNING=false
AUTOMATIC_MERGE=false
