# QRDS Phase 86 — Larger Synthetic Batch Fixture Research-Only

Gate: `PHASE86_LARGER_SYNTHETIC_BATCH_FIXTURE_RESEARCH_ONLY_READY_RESEARCH_ONLY`

Purpose:
- Create a larger synthetic journal replay batch fixture from the validated Phase 79 sample batch.
- Stress the Phase 83 batch report and Phase 84 batch report index flow with more entries.
- Keep the fixture descriptive and research-only.
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
