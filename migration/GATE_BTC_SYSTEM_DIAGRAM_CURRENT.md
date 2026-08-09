# GATE BTC / QRDS — Current System Diagram

As of: 2026-08-09

Safety boundary: `RESEARCH_ONLY` · `SHADOW_ONLY` · `NOT_APPROVED` · `ORDERS=0` · `REAL_CAPITAL=0`

```mermaid
flowchart TD
    A[Daily Research Collection on main] --> B[Immutable daily artifacts]
    B --> C[Prospective Ledgers]
    B --> D[QOS Three-Track Shadow]
    B --> E[PRL50 Position Shadow]

    C --> C1[Gateway Dynamics\nACTIVE · 4/80\nthrough 2026-08-09]
    C --> C2[LOCK25/50\nACTIVE · 3 closes\n2026-08-06..2026-08-08]
    C --> C3[V2A point-in-time data quality\nappend-only diagnostic]

    D --> D1[PIT_CONTROL]
    D --> D2[QOS_CONTROL]
    D --> D3[QOS_PRL50]
    D1 --> D4[First untouched monthly signal\n2026-08-31]
    D2 --> D4
    D3 --> D4
    D4 --> D5[First eligible execution\n2026-09-01]

    E --> E1[PRL50_POSITION\n+20% activation / 50% profit giveback]
    E1 --> E2[First untouched monthly signal\n2026-08-31]
    E2 --> E3[First eligible execution\n2026-09-01]

    F[Delta walk-forward] --> F1[86 observations\ncheckpoints 90 / 120]

    G[D50 prospective] --> G1[Validated local checkpoint\n7/30]
    G1 --> G2[Fail-closed mirror reconciliation audit\nMERGED · audit-only]
    G2 -->|full proof pack passes| G3[Mirror advance candidate]
    G2 -->|any economic-prefix change| G4[FAIL CLOSED]
    G3 --> G5[Separate reviewed mirror publication\nnot yet executed]

    H[B3 WIN A1 60m] --> H0[Automation package built and validated\nPowerShell + Windows Task Scheduler\nLOCAL INSTALL PENDING]
    H0 --> H1[v7 data-only -> canonical M1/M5 -> blind QA\nPhase B H1 untouched · 0/20]
    H1 -->|PASS structural QA| H3[Append H1 +1]
    H1 -->|FAIL| H4[No admission]
    H3 --> H2[No PnL/Sharpe/win-rate/expectancy peek before 20/20]
    H4 --> H2

    C1 --> Z[Evidence checkpoints only]
    C2 --> Z
    D5 --> Z
    E3 --> Z
    F1 --> Z
    G5 --> Z
    H2 --> Z

    Z --> P{Promotion gate}
    P -->|Insufficient evidence| R[Remain research/shadow]
    P -->|Future explicit approval only| O[Operational review]

    R --> S[ORDERS=0 · CAPITAL=0]
```

## Frozen sequencing

1. Keep Daily Research Collection running without methodology changes.
2. Keep Gateway and LOCK25/50 prospective ledgers append-only.
3. Do not backfill QOS Three-Track or PRL50; wait for the first untouched 2026-08-31 signal.
4. Delta continues automatically to 90 and 120 observations without recalibration.
5. D50 preserves validated frozen/local history. The audit-only mirror reconciler is now merged; it may emit only a `PASS_MIRROR_ADVANCE_CANDIDATE` after the full provenance proof pack passes. Runtime publication remains a separate reviewed step, and any economic-field change fails closed.
6. B3 Phase B automation package is built and validated. It remains local-install pending; after install, Windows Task Scheduler runs v7 in data-only mode, passes canonical M1/M5 to blind QA, admits only structurally qualified sessions, and freezes automatically at 20/20.
7. B3 Phase B remains blind until H1 reaches 20/20 qualified sessions; only data-quality inspection is allowed beforehand.
8. No operational promotion, real capital, or order generation is authorized by this diagram.
