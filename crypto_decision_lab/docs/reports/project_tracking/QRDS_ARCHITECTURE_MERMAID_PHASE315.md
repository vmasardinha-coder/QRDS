# QRDS Architecture Mermaid — Phase 315

```mermaid
flowchart TD
    A[Public multi-source history] --> B[Controlled features v2]
    B --> C[Closed registry: 24 hypotheses]
    C --> D[Nested walk-forward v2]
    D --> E[Temporal stability audit]
    E --> F[Regime concentration audit]
    F --> G[Hypothesis dependence audit]
    G --> H[Extreme cost and liquidity audit]
    H --> I[Timestamp sensitivity audit]
    I --> J{Eligibility gates}
    J -->|Failed: 7| K[Close current family research-only]
    J -->|All pass| L[Manual freeze review only]
    K --> M[NO_ACTION_RESEARCH_ONLY]
    L --> M
    M --> N[Forward clock inactive]
    N --> O[Paper and real capital blocked]
```

**VOCE ESTA AQUI:** `CLOSE_CURRENT_FAMILY_RESEARCH_ONLY`. No immutable candidate freeze exists and
historical evidence has zero credit in the forward clock.
