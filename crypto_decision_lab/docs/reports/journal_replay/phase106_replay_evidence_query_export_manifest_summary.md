# QRDS Phase 106 — Replay Evidence Query Export Manifest Research-Only

Gate: `PHASE106_REPLAY_EVIDENCE_QUERY_EXPORT_MANIFEST_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Creates a descriptive export manifest for the Phase 101–105 replay evidence query batch.

Allowed exports:
- JSON manifest
- Markdown summary
- HTML portal stub

Blocked exports:
- trading signal export
- allocation export

Locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- decision_layer_allowed: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
- full_suite_status: SKIPPED_LOCAL_ECONOMICAL
