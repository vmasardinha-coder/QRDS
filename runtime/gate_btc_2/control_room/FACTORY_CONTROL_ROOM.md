# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-14T02:44:46.258404+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **35**
- Latest ledger: **2026-11-13**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-13`)
- Triggered cells: **30**
- Cells at 60/60: **0**
- Trigger range: **0–12 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **8**
- `TRIGGER`: **2**
- `WARMUP_PENDING`: **570**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-13`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (43 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **389** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-14T00:55:17.316825Z`
- `F-XVOL-SURFACE`: **389** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-14T00:55:17.274032Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 26 to 26 | 0 to 0 |
| 20 | 5 | 26 to 26 | 0 to 0 |
| 60 | 6 | 26 to 26 | 34 to 34 |
| 80 | 10 | 26 to 26 | 54 to 54 |
| 120 | 26 | 26 to 26 | 94 to 94 |
| 160 | 16 | 26 to 26 | 134 to 134 |
| 200 | 256 | 19 to 26 | 174 to 181 |
| 252 | 256 | 19 to 26 | 226 to 233 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
