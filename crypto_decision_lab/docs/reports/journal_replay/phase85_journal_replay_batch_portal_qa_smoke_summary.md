# QRDS Phase 85 — Journal Replay Batch Portal QA Smoke Research-Only

Gate: `PHASE85_JOURNAL_REPLAY_BATCH_PORTAL_QA_SMOKE_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Run a local/economical QA smoke over the Phase 84 journal replay batch report portal artifacts.
- Check required JSON/HTML files.
- Check required research-only safety markers.
- Detect forbidden operational language.
- Keep full suite skipped locally until checkpoint.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
- full_suite_status: SKIPPED_LOCAL_ECONOMICAL
