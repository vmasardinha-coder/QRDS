# QRDS Phase 76 — Journal Replay Evidence Scorecard V2 Research-Only

Gate: `PHASE76_JOURNAL_REPLAY_EVIDENCE_SCORECARD_V2_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Consolidate replay dry-run, aggregate metrics, distribution diagnostics and quality flags.
- Produce a single descriptive evidence scorecard.
- Explicitly list blockers to edge.
- Keep scorecard non-edge and non-decision.
- Keep signals, recommendations, allocations, shadow decisions, promotion, safe-apply and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
