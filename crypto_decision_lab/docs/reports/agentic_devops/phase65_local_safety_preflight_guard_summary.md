# QRDS Phase 65 — Local Safety Preflight Guard Research-Only

Gate: `PHASE65_LOCAL_SAFETY_PREFLIGHT_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Run a local preflight check before accepting phase/agent patches.
- Require focused tests and full suite pass.
- Check safety flags.
- Reject forbidden operational terms.
- Flag watched paths for human review.
- Keep auto-apply, safe-apply, promotion and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
