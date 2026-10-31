# GATE BTC 2.0 — Factory Control Room

Generated: `2026-10-31T05:45:48.115765+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **26**
- Latest ledger: **2026-10-30**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-10-30`)
- Triggered cells: **15**
- Cells at 60/60: **0**
- Trigger range: **0–7 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **1**
- `TRIGGER`: **4**
- `WARMUP_PENDING`: **575**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-10-30`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (40 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **278** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-31T05:44:42.990954Z`
- `F-XVOL-SURFACE`: **278** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-31T05:44:42.965909Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 17 to 17 | 0 to 0 |
| 20 | 5 | 17 to 17 | 3 to 3 |
| 60 | 6 | 17 to 17 | 43 to 43 |
| 80 | 10 | 17 to 17 | 63 to 63 |
| 120 | 26 | 17 to 17 | 103 to 103 |
| 160 | 16 | 17 to 17 | 143 to 143 |
| 200 | 256 | 10 to 17 | 183 to 190 |
| 252 | 256 | 10 to 17 | 235 to 242 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
