# QRDS / QOS — Architecture

## Principle

Build and preserve a research-only pipeline first, with hard safety boundaries, immutable prospective evidence and fail-closed admission.

## Current GATE BTC architecture

Status snapshot: **2026-08-09**.

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
            ├───────────────────────────────────────────────────────┐
            ▼                                                       ▼
 ┌──────────────────────────────┐                    ┌──────────────────────────────┐
 │ LOCK25/50 prospective ledger │                    │ D50 qualification            │
 │ ACTIVE                       │                    │ ACTIVE — 6 / 7              │
 │ 3 valid closes               │                    │ one valid snapshot remains  │
 │ 2026-08-06 → 2026-08-08      │                    └──────────────┬───────────────┘
 │ 6 tracks:                    │                                   │
 │ Moderada / Ultra ×           │                                   ▼
 │ Control / LOCK25 / LOCK50    │                    ┌──────────────────────────────┐
 └──────────────────────────────┘                    │ D50 immutable ledger         │
                                                     │ FAIL-CLOSED BLOCKED — 4/30  │
                                                     │ provenance-only source       │
                                                     │ revision repair pending      │
                                                     │ economic rows must not move │
                                                     └──────────────────────────────┘

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

## Measurement-state interpretation

- **ACTIVE** means the frozen prospective mechanism is collecting admissible evidence; it does not mean operational approval.
- **CALENDAR-GATED** means the mechanism is installed but cannot create a valid observation before its frozen date.
- **FAIL-CLOSED BLOCKED** means evidence accumulation stops until the stated provenance/integrity defect is repaired without changing frozen economics.
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
