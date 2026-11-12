# GATE BTC 2.0 — Factory Control Room

Generated: `2026-11-12T16:52:13.251145+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **33**
- Latest ledger: **2026-11-11**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-11-11`)
- Triggered cells: **30**
- Cells at 60/60: **0**
- Trigger range: **0–11 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **7**
- `TRIGGER`: **3**
- `WARMUP_PENDING`: **570**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-11-11`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (46 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **378** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-12T16:50:42.312061Z`
- `F-XVOL-SURFACE`: **378** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-11-12T16:50:42.265723Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 24 to 24 | 0 to 0 |
| 20 | 5 | 24 to 24 | 0 to 0 |
| 60 | 6 | 24 to 24 | 36 to 36 |
| 80 | 10 | 24 to 24 | 56 to 56 |
| 120 | 26 | 24 to 24 | 96 to 96 |
| 160 | 16 | 24 to 24 | 136 to 136 |
| 200 | 256 | 17 to 24 | 176 to 183 |
| 252 | 256 | 17 to 24 | 228 to 235 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
