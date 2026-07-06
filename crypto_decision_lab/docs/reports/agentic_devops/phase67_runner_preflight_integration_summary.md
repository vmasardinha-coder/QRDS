# QRDS Phase 67 — Runner Preflight Integration Research-Only

Gate: `PHASE67_RUNNER_PREFLIGHT_INTEGRATION_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Integrate local preflight into the next-phase runner.
- Require the runner to pass preflight before validation.
- Keep auto-apply, safe-apply, promotion and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
