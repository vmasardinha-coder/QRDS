# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-07T00:53:55.831326+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **30**
- Latest ledger: **2026-11-06**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-06`)
- Triggered cells: **21**
- Cells at 60/60: **0**
- Trigger range: **0–10 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **5**
- `TRIGGER`: **5**
- `WARMUP_PENDING`: **570**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-06`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (43 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **334** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-07T00:52:33.878796Z`
- `F-XVOL-SURFACE`: **334** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-07T00:52:33.842896Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 21 to 21 | 0 to 0 |
| 20 | 5 | 21 to 21 | 0 to 0 |
| 60 | 6 | 21 to 21 | 39 to 39 |
| 80 | 10 | 21 to 21 | 59 to 59 |
| 120 | 26 | 21 to 21 | 99 to 99 |
| 160 | 16 | 21 to 21 | 139 to 139 |
| 200 | 256 | 14 to 21 | 179 to 186 |
| 252 | 256 | 14 to 21 | 231 to 238 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
