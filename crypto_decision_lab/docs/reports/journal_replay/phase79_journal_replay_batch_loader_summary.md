# QRDS Phase 79 — Journal Replay Batch Loader Research-Only

Gate: `PHASE79_JOURNAL_REPLAY_BATCH_LOADER_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Load external/staging JSON batches for journal replay dry-run.
- Validate batch structure and entries.
- Run descriptive replay and scorecard on loaded entries.
- Keep loader, replay, edge, shadow, decision, signals, recommendations, allocations, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
