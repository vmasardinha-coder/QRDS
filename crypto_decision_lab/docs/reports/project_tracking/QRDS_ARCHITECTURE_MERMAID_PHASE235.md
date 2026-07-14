# QRDS Architecture - Phase 235

```mermaid
flowchart LR
  A[Registry inputs] --> B[Process-local cache]
  B --> C[Defensive copy]
  C --> D[DAG recomputation guard]
  D --> E[Performance and leak guards]
  E --> F[JUnit resume integrity]
  F --> G[Phase 235 checkpoint]
  G --> H[BLOCKED_RESEARCH_ONLY]
```
