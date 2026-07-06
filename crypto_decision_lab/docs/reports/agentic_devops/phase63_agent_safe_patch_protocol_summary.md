# QRDS Phase 63 — Agent Safe Patch Protocol Research-Only

Gate: `PHASE63_AGENT_SAFE_PATCH_PROTOCOL_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Define which agent patches are safe technical patches versus blocked architecture/safety patches.
- Keep auto-apply disabled.
- Require human review.
- Reject safety lock, edge, shadow, decision, promotion or canonical-write changes.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
