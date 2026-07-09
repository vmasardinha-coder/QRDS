# QRDS Phase 162 - Shadow Evidence Replay Input Builder Research-Only

Gate: PHASE162_SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER_RESEARCH_ONLY_READY_RESEARCH_ONLY

Builds a research-only replay input for shadow evidence replay.

Required fields:
- replay_input_id
- candidate_id
- evidence_quality_score
- evidence_quality_label
- replay_validity_status
- risk_status
- shadow_simulation_status

Forbidden fields:
- decision
- recommendation
- trading_signal
- allocation
- position_size
- order_payload
- safe_apply_payload

Boundary:
- no decision payload
- no trading signal
- no recommendation
- no allocation
- no order payload
- no safe-apply
- no canonical write
