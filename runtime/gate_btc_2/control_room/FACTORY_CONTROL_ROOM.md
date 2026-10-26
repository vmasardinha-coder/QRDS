# GATE BTC 2.0 — Factory Control Room

Generated: `2026-10-26T21:04:14.214036+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **21**
- Latest ledger: **2026-10-23**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-10-23`)
- Triggered cells: **15**
- Cells at 60/60: **0**
- Trigger range: **0–3 / 60**

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
- Latest physically observed symbol: `WINZ26` (session `2026-10-23`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (46 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **243** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-26T21:03:10.044528Z`
- `F-XVOL-SURFACE`: **243** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-26T21:03:09.999763Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 13 to 13 | 0 to 0 |
| 20 | 5 | 13 to 13 | 7 to 7 |
| 60 | 6 | 13 to 13 | 47 to 47 |
| 80 | 10 | 13 to 13 | 67 to 67 |
| 120 | 26 | 13 to 13 | 107 to 107 |
| 160 | 16 | 13 to 13 | 147 to 147 |
| 200 | 256 | 7 to 13 | 187 to 193 |
| 252 | 256 | 7 to 13 | 239 to 245 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
