# QRDS Phase 103 — Replay Evidence Query CLI Dry-Run Research-Only

Gate: `PHASE103_REPLAY_EVIDENCE_QUERY_CLI_DRY_RUN_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Creates a dry-run local query layer for evidence lookup.

Allowed:
- by_phase
- by_tag
- by_checkpoint
- by_review_status

Blocked:
- decision_query
- signal_query
- allocation_query

Locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- decision_layer_allowed: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
