# QRDS Phase 80 — Journal Replay Batch Quarantine Research-Only

Gate: `PHASE80_JOURNAL_REPLAY_BATCH_QUARANTINE_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Quarantine invalid external/staging journal replay batches.
- Preserve validation errors and invalid entries for human review.
- Prevent invalid batches from being interpreted as evidence.
- Keep loader execution, replay execution, edge validation, signals, recommendations, allocations, shadow decisions, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
