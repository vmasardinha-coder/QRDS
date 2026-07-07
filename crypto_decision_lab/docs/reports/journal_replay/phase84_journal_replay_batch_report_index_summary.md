# QRDS Phase 84 — Journal Replay Batch Report Index Research-Only

Gate: `PHASE84_JOURNAL_REPLAY_BATCH_REPORT_INDEX_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Build a descriptive index of journal replay batch reports.
- Surface batch ID, report status, row counts, evidence status and human review requirement.
- Keep batch reports from being interpreted as edge evidence.
- Keep loader execution, replay execution, edge validation, signals, recommendations, allocations, shadow decisions, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
