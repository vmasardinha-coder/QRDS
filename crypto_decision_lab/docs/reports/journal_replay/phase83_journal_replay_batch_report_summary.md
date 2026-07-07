# QRDS Phase 83 — Journal Replay Batch Report Research-Only

Gate: `PHASE83_JOURNAL_REPLAY_BATCH_REPORT_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Generate a consolidated descriptive report for a journal replay batch.
- Combine batch validation, replay dry-run, aggregate metrics, distribution diagnostics, quality flags and evidence scorecard.
- Mark invalid or unsafe batches as NEEDS_REVIEW_RESEARCH_ONLY.
- Keep loader execution, replay execution, edge validation, signals, recommendations, allocations, shadow decisions, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
