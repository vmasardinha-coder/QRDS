# GATE BTC 2.0 — Factory Control Room

Generated: `2026-10-23T00:53:56.144785+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **20**
- Latest ledger: **2026-10-22**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-10-22`)
- Triggered cells: **12**
- Cells at 60/60: **0**
- Trigger range: **0–2 / 60**

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
- Latest physically observed symbol: `WINZ26` (session `2026-10-22`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (46 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **209** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-22T23:25:05.000158Z`
- `F-XVOL-SURFACE`: **209** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-22T23:25:04.964845Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 12 to 12 | 0 to 0 |
| 20 | 5 | 12 to 12 | 8 to 8 |
| 60 | 6 | 12 to 12 | 48 to 48 |
| 80 | 10 | 12 to 12 | 68 to 68 |
| 120 | 26 | 12 to 12 | 108 to 108 |
| 160 | 16 | 12 to 12 | 148 to 148 |
| 200 | 256 | 6 to 12 | 188 to 194 |
| 252 | 256 | 6 to 12 | 240 to 246 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
