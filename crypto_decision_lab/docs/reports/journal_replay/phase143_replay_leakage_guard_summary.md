# QRDS Phase 143 - Replay Leakage Guard Research-Only

Gate: PHASE143_REPLAY_LEAKAGE_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY

Adds a research-only replay leakage guard.

Checks:
- no future label usage
- no feature lookahead
- valid feature/label timestamp ordering

Boundary:
- leakage guard is research-only
- valid for decision: False
- no edge validation
- no trading signal
- no allocation
- no decision
- no canonical write
