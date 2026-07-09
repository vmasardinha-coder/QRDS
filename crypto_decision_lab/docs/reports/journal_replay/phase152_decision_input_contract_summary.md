# QRDS Phase 152 - Decision Input Contract Research-Only

Gate: PHASE152_DECISION_INPUT_CONTRACT_RESEARCH_ONLY_READY_RESEARCH_ONLY

Adds a strict research-only input contract for future shadow decision readiness.

Required fields:
- candidate_id
- evidence_quality_score
- replay_validity_status
- risk_status
- ruin_hit_count
- total_exposure_fraction

Forbidden fields:
- order_side
- order_qty
- order_price
- position_size
- allocation_weight
- recommendation
- trading_signal

Boundary:
- no order payload
- no position sizing
- no allocation
- no recommendation
- no trading signal
- no decision
- no canonical write
