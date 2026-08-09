# QRDS / QOS — Architecture

## Principle

Build and preserve a research-only pipeline first, with hard safety boundaries, immutable prospective evidence and fail-closed admission.

## Current GATE BTC architecture

Status snapshot: **2026-08-09**.

The live local D50 evidence is newer than the GitHub runtime mirror. The diagram therefore shows both states explicitly instead of silently treating the stale mirror as current.

```text
                                   GATE BTC — RESEARCH / SHADOW ONLY

 Public sources / frozen inputs
             │
             ▼
 ┌──────────────────────────────────────┐
 │ GATE BTC Daily Research Collection   │
 │ V2A + Delta + Gateway                │
 │ deterministic / fail-closed          │
 └──────────────────┬───────────────────┘
                    │ validated daily artifact only
                    ▼
 ┌──────────────────────────────────────┐
 │ Safety + provenance admission        │
 │ research_only = true                 │
 │ shadow_only = true                   │
 │ not_approved = true                  │
 │ orders = 0 / capital = 0             │
 └───────┬──────────────┬───────────────┘
         │              │
         │              └──────────────────────────────┐
         ▼                                             ▼
 ┌──────────────────────┐                    ┌──────────────────────┐
 │ Gateway Dynamics     │                    │ Delta Walk-Forward   │
 │ ACTIVE               │                    │ ACTIVE               │
 │ 4 / 80               │                    │ 86 → gates 90 / 120  │
 │ latest: 2026-08-09   │                    └──────────────────────┘
 │ next:   2026-08-10   │
 └──────────┬───────────┘
            │
            ├────────────────────────────────────────────────────────┐
            ▼                                                        ▼
 ┌──────────────────────────────┐                    ┌───────────────────────────────┐
 │ LOCK25/50 prospective ledger │                    │ D50 LOCAL LIVE               │
 │ ACTIVE                       │                    │ PASS_DAILY_UPDATE             │
 │ 3 valid closes               │                    │ economic ledger 7 / 30       │
 │ 2026-08-06 → 2026-08-08      │                    │ latest: 2026-08-08           │
 │ 6 tracks:                    │                    │ backfill 04/08 + 05/08       │
 │ Moderada / Ultra ×           │                    │ excluded from prospective     │
 │ Control / LOCK25 / LOCK50    │                    │ orders=0 / capital=0         │
 └──────────────────────────────┘                    └──────────────┬────────────────┘
                                                                    │ reconcile evidence,
                                                                    │ never rewrite history
                                                                    ▼
                                                     ┌───────────────────────────────┐
                                                     │ D50 GITHUB RUNTIME MIRROR    │
                                                     │ STALE — 4 / 30               │
                                                     │ published state: 2026-08-06  │
                                                     │ overlap must be audited      │
                                                     │ before mirror advancement    │
                                                     └───────────────────────────────┘

 D50 DATA-QUALITY VIEW
 local current chain: 1 / 7 after 07/08 network failure
 prior historical chain: 7 / 7 preserved
 GitHub runtime mirror: 6 / 7 (stale; do not overwrite local evidence)

                     ┌─────────────────────────────────────────────┐
                     │ Monthly point-in-time signal boundary       │
                     │ first untouched signal: 2026-08-31         │
                     └────────────────────┬────────────────────────┘
                                          │
                         ┌────────────────┴────────────────┐
                         ▼                                 ▼
              ┌────────────────────────┐       ┌────────────────────────┐
              │ QOS Three-Track Shadow │       │ PRL50_POSITION Shadow  │
              │ CALENDAR-GATED 0 / 3   │       │ WAITING FIRST SIGNAL   │
              │ PIT_CONTROL            │       │ +20% activation        │
              │ QOS_CONTROL            │       │ 50% profit giveback    │
              │ QOS_PRL50              │       │ first exec: 2026-09-01│
              └────────────────────────┘       └────────────────────────┘

                              │
                              ▼
                   ┌────────────────────────┐
                   │ Evidence / Reports     │
                   │ immutable ledgers      │
                   │ frozen contracts       │
                   │ audit / comparison     │
                   └────────────────────────┘

 HARD BOUNDARY ACROSS THE WHOLE GRAPH
 RESEARCH_ONLY · SHADOW_ONLY · NOT_APPROVED · PROMOTION PROHIBITED
 ORDERS_GENERATED = 0 · REAL_CAPITAL_USED = 0
```

## D50 reconciliation boundary

The local D50 autopilot has already advanced beyond the stale GitHub mirror. Reconciliation must therefore be **forward-only and non-destructive**:

```text
local validated prospective tip = 7/30 through 2026-08-08
github runtime mirror           = 4/30 published through 2026-08-06
reset                           = forbidden
rewrite admitted economic row   = forbidden
existing-date counter inflation = forbidden
historical backfill as live     = forbidden
provenance-only diagnostic      = allowed, immutable
new admissible dates            = append only after overlap verification
```

The dates 2026-08-04 and 2026-08-05 are explicitly recorded by the local updater as historical backfill exclusions and must not be retroactively counted as prospective observations.

## Measurement-state interpretation

- **ACTIVE** means the frozen prospective mechanism is collecting admissible evidence; it does not mean operational approval.
- **CALENDAR-GATED** means the mechanism is installed but cannot create a valid observation before its frozen date.
- **STALE MIRROR** means a published copy trails a newer validated source. It must be reconciled by overlap/invariant checks, never by resetting or blindly replacing the source of truth.
- A counter advances only on a genuinely admissible observation under the already-frozen contract.

## Safety architecture

Every boundary must preserve:

```text
research_allowed = True
operational_decision_allowed = False
api_key_required = False
api_key_present = False
account_connection_required = False
orders_generated = False
real_capital_used = False
```

For the current prospective stack, the equivalent project-level assertions are:

```text
research_only = True
shadow_only = True
not_approved = True
promotion_allowed = False
orders_generated = 0
real_capital_used = 0
```

No diagram state is an authorization to trade. Runtime evidence may advance only through the corresponding frozen, fail-closed workflow.
