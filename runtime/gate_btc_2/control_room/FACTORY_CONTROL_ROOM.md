# GATE BTC 2.0 — Factory Control Room

Generated: `2026-10-22T00:52:21.556849+00:00`

## Funnel
- Reclassified: **2560**
- Experimental shadow eligible: **580**
- Active: **580**
- Ledger sessions: **19**
- Latest ledger: **2026-10-21**
- Latest collector: **SESSION_CAPTURED_ZERO_CREDIT** (`2026-10-21`)
- Triggered cells: **6**
- Cells at 60/60: **0**
- Trigger range: **0–1 / 60**

## Latest prospective session states
- `NO_SIGNAL`: **3**
- `TRIGGER`: **2**
- `WARMUP_PENDING`: **575**

## 3D family states
- `CONTINUE_EXPERIMENTAL_SHADOW`: **580**

## 3D cell states
- `AWAITING_FORWARD_TRIGGERS`: **1740**

## Source
- Historical binding snapshot: `FORWARD_SOURCE_BOUND` / `WINV26`
- Latest physically observed symbol: `WINZ26` (session `2026-10-21`; source QA=None)
- Waiting source semantics: **0**
- Discovery candidate inventory (separate authority): `AVAILABLE_SOURCE_CANDIDATE` (46 records; admitted=False)

## External prospective lanes
- `F-XMM-INVENTORY`: **199** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-21T23:22:32.098966Z`
- `F-XVOL-SURFACE`: **199** records · `PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING` · latest `2026-10-21T23:22:32.056154Z`

## Frozen prior-feature coverage

| Lookback | Families | Prior feature observations | Additional prior observations |
|---|---:|---:|---:|
| 10 | 5 | 11 to 11 | 0 to 0 |
| 20 | 5 | 11 to 11 | 9 to 9 |
| 60 | 6 | 11 to 11 | 49 to 49 |
| 80 | 10 | 11 to 11 | 69 to 69 |
| 120 | 26 | 11 to 11 | 109 to 109 |
| 160 | 16 | 11 to 11 | 149 to 149 |
| 200 | 256 | 5 to 11 | 189 to 195 |
| 252 | 256 | 5 to 11 | 241 to 247 |

Coverage is not a signal. A later eligible session, its current feature, nonzero MAD and the frozen trigger remain required.

## Boundary
`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`

Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.
