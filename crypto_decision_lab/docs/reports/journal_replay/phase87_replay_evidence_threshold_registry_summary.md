# QRDS Phase 87 — Replay Evidence Threshold Registry Research-Only

Gate: `PHASE87_REPLAY_EVIDENCE_THRESHOLD_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Define explicit descriptive thresholds for replay evidence interpretation.
- Separate insufficient sample, needs-review and research-candidate-threshold-pass statuses.
- Make clear that passing thresholds does not validate edge.
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
