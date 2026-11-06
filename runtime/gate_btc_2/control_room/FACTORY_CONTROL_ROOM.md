# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-06T10:48:46.342987+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **29**
- Latest ledger: **2026-11-05**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-05`)
- Triggered cells: **15**
- Cells at 60/60: **0**
- Trigger range: **0–10 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **4**
- `TRIGGER`: **1**
- `WARMUP_PENDING`: **575**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-05`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (46 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **329** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-06T10:47:27.242724Z`
- `F-XVOL-SURFACE`: **329** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-06T10:47:27.213356Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 20 to 20 | 0 to 0 |
| 20 | 5 | 20 to 20 | 0 to 0 |
| 60 | 6 | 20 to 20 | 40 to 40 |
| 80 | 10 | 20 to 20 | 60 to 60 |
| 120 | 26 | 20 to 20 | 100 to 100 |
| 160 | 16 | 20 to 20 | 140 to 140 |
| 200 | 256 | 13 to 20 | 180 to 187 |
| 252 | 256 | 13 to 20 | 232 to 239 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
