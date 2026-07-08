# QRDS Phase 125 - Review Portal UX Batch Checkpoint Research-Only

Gate: PHASE125_REVIEW_PORTAL_UX_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY

Checkpoint for the Phase 121-125 review portal UX batch.

Checks:
- Phase 121 review portal index page
- Phase 122 serve root fix
- Phase 123 portal link smoke test
- Phase 124 one-command review portal runner

Run:
.\tools\run_review_portal_research_only.ps1

Local index URL:
http://localhost:8765/index.html

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
