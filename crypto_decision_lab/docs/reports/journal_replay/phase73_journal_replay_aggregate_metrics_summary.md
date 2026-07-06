# QRDS Phase 73 — Journal Replay Aggregate Metrics Research-Only

Gate: `PHASE73_JOURNAL_REPLAY_AGGREGATE_METRICS_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Aggregate dry-run journal replay results.
- Produce descriptive-only metrics such as paper PnL, win/loss counts and by-asset summaries.
- Keep metrics descriptive only.
- Keep edge, shadow, decision, signals, recommendations, allocations, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
