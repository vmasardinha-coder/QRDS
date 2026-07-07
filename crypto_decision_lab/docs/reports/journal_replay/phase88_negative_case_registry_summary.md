# QRDS Phase 88 — Negative Case Registry Research-Only

Gate: `PHASE88_NEGATIVE_CASE_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Register negative replay evidence cases that must not be interpreted as edge.
- Cover small sample, invalid rows, concentration, outliers and drawdown-like warnings.
- Prevent false confidence from descriptive replay outputs.
- Keep full suite skipped locally until checkpoint.

Permanent locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- promotion_allowed: False
- safe_apply_allowed: False
- canonical_data_writes: 0
- full_suite_status: SKIPPED_LOCAL_ECONOMICAL
