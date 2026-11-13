# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-13T18:50:22.021027+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **34**
- Latest ledger: **2026-11-12**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-12`)
- Triggered cells: **30**
- Cells at 60/60: **0**
- Trigger range: **0–12 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **4**
- `TRIGGER`: **6**
- `WARMUP_PENDING`: **570**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-12`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (39 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **386** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-13T18:48:46.827547Z`
- `F-XVOL-SURFACE`: **386** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-13T18:48:46.786416Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 25 to 25 | 0 to 0 |
| 20 | 5 | 25 to 25 | 0 to 0 |
| 60 | 6 | 25 to 25 | 35 to 35 |
| 80 | 10 | 25 to 25 | 55 to 55 |
| 120 | 26 | 25 to 25 | 95 to 95 |
| 160 | 16 | 25 to 25 | 135 to 135 |
| 200 | 256 | 18 to 25 | 175 to 182 |
| 252 | 256 | 18 to 25 | 227 to 234 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
