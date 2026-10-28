# GATE BTC 2.0 — Factory Control Room

Generated: `2026-10-28T05:27:07.087837+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **23**
- Latest ledger: **2026-10-27**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-10-27`)
- Triggered cells: **15**
- Cells at 60/60: **0**
- Trigger range: **0–4 / 60**

## Latest prospective session states
- `FEATURE_UNAVAILABLE`: **64**
- `TRIGGER`: **5**
- `WARMUP_PENDING`: **511**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-10-27`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (43 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **253** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-28T05:26:06.228539Z`
- `F-XVOL-SURFACE`: **253** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-28T05:26:06.186920Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 14 to 14 | 0 to 0 |
| 20 | 5 | 14 to 14 | 6 to 6 |
| 60 | 6 | 14 to 14 | 46 to 46 |
| 80 | 10 | 14 to 14 | 66 to 66 |
| 120 | 26 | 14 to 14 | 106 to 106 |
| 160 | 16 | 14 to 14 | 146 to 146 |
| 200 | 256 | 7 to 14 | 186 to 193 |
| 252 | 256 | 7 to 14 | 238 to 245 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
