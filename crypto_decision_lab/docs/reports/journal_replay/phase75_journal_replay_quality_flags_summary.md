# QRDS Phase 75 — Journal Replay Quality Flags Research-Only

Gate: `PHASE75_JOURNAL_REPLAY_QUALITY_FLAGS_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Add descriptive-only quality flags for dry-run journal replay.
- Flag small sample, invalid rows, asset concentration, outliers and drawdown-like sequences.
- Keep quality flags explicitly non-edge and non-decision.
- Keep signals, recommendations, allocations, shadow decisions, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
