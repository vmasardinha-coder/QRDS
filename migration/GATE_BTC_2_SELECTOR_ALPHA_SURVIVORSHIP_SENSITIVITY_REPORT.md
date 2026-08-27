# GATE BTC 2.0 — Survivorship Sensitivity Report

STATUS=FAIL_SELECTOR_ALPHA_ABSENT_AND_NOT_ROBUST__HYPOTHESIS_CLOSED

## Observed hash-sealed result

| Arm | Direct alpha vs unfiltered / week | HAC 95% CI | Conclusion |
|---|---:|---:|---|
| Moderada | -0.2530% | [-1.1497%, 0.6438%] | non-positive |
| Ultra | -0.1594% | [-0.8672%, 0.5483%] | non-positive |

## Seeded random missingness

| Arm | p05 | Median | p95 | P(alpha > 0) |
|---|---:|---:|---:|---:|
| Moderada | -0.3280% | -0.2580% | -0.1527% | 0.30% |
| Ultra | -0.2236% | -0.1619% | -0.0758% | 0.70% |

## Required answers

- Loss intensity that eliminates observed alpha: Moderada=0.0; Ultra=0.0 (both are already non-positive without synthetic loss).
- Selector-favourable rescue interval: Moderada=[0.44, 0.45]; Ultra=[0.28, 0.29].
- Ranking survives adversarial bounds: false.
- Selector superior under bounds: false.
- A sign change is mathematically possible in at least one selector-favourable synthetic bound: true. This is sensitivity, not observed evidence.

## Decision

The current frozen selector alpha hypothesis is refuted and closed without retune. Phase 4–7 are not executed because the Phase-3 stop gate fired.

Synthetic values remain outside the official dataset. RESEARCH_ONLY=true; SHADOW_ONLY=true; NOT_APPROVED=true; ENGINE_FEED=false; ORDERS=0; REAL_CAPITAL=R$0.
