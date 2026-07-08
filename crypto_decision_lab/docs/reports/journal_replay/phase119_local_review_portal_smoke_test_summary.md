# QRDS Phase 119 — Local Review Portal Smoke Test Research-Only

Gate: `PHASE119_LOCAL_REVIEW_PORTAL_SMOKE_TEST_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Adds a local smoke test for the review portal package.

Checks:
- portal HTML exists
- serve script exists
- portal contains research-only boundary
- portal contains no-decision boundary
- serve script uses local HTTP server
- serve script declares the local URL

Boundary:
- research-only
- no edge validation
- no trading signal
- no allocation
- no safe-apply
- no promotion
- no canonical write
