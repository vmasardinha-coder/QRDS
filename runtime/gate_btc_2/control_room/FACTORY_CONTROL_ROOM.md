# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-04T22:55:09.283511+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **28**
- Latest ledger: **2026-11-04**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-04`)
- Triggered cells: **15**
- Cells at 60/60: **0**
- Trigger range: **0–9 / 60**

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
- Latest physically observed symbol: `WINZ26` (session `2026-11-04`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (40 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **318** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-04T22:53:56.383670Z`
- `F-XVOL-SURFACE`: **318** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-04T22:53:56.347111Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 19 to 19 | 0 to 0 |
| 20 | 5 | 19 to 19 | 1 to 1 |
| 60 | 6 | 19 to 19 | 41 to 41 |
| 80 | 10 | 19 to 19 | 61 to 61 |
| 120 | 26 | 19 to 19 | 101 to 101 |
| 160 | 16 | 19 to 19 | 141 to 141 |
| 200 | 256 | 12 to 19 | 181 to 188 |
| 252 | 256 | 12 to 19 | 233 to 240 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
