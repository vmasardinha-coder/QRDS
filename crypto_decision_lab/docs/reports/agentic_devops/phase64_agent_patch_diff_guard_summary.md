# QRDS Phase 64 — Agent Patch Diff Guard Research-Only

Gate: `PHASE64_AGENT_PATCH_DIFF_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Scan proposed agent diffs for forbidden safety/decision/operational changes.
- Flag watched paths for human review.
- Keep auto-apply and safe-apply disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
