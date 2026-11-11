# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-11T19:49:03.849803+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **32**
- Latest ledger: **2026-11-10**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-10`)
- Triggered cells: **30**
- Cells at 60/60: **0**
- Trigger range: **0–10 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **3**
- `TRIGGER`: **7**
- `WARMUP_PENDING`: **570**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-10`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (43 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **372** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-11T19:47:19.821559Z`
- `F-XVOL-SURFACE`: **372** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-11T19:47:19.742914Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 23 to 23 | 0 to 0 |
| 20 | 5 | 23 to 23 | 0 to 0 |
| 60 | 6 | 23 to 23 | 37 to 37 |
| 80 | 10 | 23 to 23 | 57 to 57 |
| 120 | 26 | 23 to 23 | 97 to 97 |
| 160 | 16 | 23 to 23 | 137 to 137 |
| 200 | 256 | 16 to 23 | 177 to 184 |
| 252 | 256 | 16 to 23 | 229 to 236 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
