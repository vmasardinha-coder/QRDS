# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-10T06:51:16.205112+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **31**
- Latest ledger: **2026-11-09**
- Latest collector: **WAIT_DAILY_BATCH_WINDOW** (`None`)
- Triggered cells: **21**
- Cells at 60/60: **0**
- Trigger range: **0–10 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **9**
- `TRIGGER`: **1**
- `WARMUP_PENDING`: **570**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-09`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (46 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **360** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-10T06:50:01.702905Z`
- `F-XVOL-SURFACE`: **360** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-10T06:50:01.667782Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 22 to 22 | 0 to 0 |
| 20 | 5 | 22 to 22 | 0 to 0 |
| 60 | 6 | 22 to 22 | 38 to 38 |
| 80 | 10 | 22 to 22 | 58 to 58 |
| 120 | 26 | 22 to 22 | 98 to 98 |
| 160 | 16 | 22 to 22 | 138 to 138 |
| 200 | 256 | 15 to 22 | 178 to 185 |
| 252 | 256 | 15 to 22 | 230 to 237 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
