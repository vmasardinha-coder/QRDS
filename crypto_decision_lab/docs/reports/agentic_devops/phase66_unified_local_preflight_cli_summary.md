# QRDS Phase 66 — Unified Local Preflight CLI Research-Only

Gate: `PHASE66_UNIFIED_LOCAL_PREFLIGHT_CLI_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Command:
```bash
bash qrds_local_preflight.sh
```

Purpose:
- Provide one local preflight command before accepting agent/phase patches.
- Check tests, safety flags, forbidden terms and watched files.
- Keep human review required.
- Keep auto-apply, safe-apply, promotion and canonical writes disabled.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
