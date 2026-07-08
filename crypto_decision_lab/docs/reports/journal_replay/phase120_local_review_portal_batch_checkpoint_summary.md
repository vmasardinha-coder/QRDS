# QRDS Phase 120 - Local Review Portal Batch Checkpoint Research-Only

Gate: PHASE120_LOCAL_REVIEW_PORTAL_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY

Checkpoint for the Phase 116-120 local review portal batch.

Checks:
- Phase 116 export review runbook
- Phase 117 review portal asset index
- Phase 118 local review serve script
- Phase 119 local review portal smoke test

Local portal:
http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html

Run:
.\tools\serve_review_portal_research_only.ps1

Boundary:
- approval effect: NONE_RESEARCH_ONLY
- no edge validation
- no trading signal
- no recommendation
- no allocation
- no decision
- no safe-apply
- no promotion
- no canonical write
