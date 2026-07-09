# QRDS Phase 144 - Replay Validity Preflight Research-Only

Gate: PHASE144_REPLAY_VALIDITY_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY

Adds a research-only replay validity preflight.

Checks:
- Phase 141 replay validity requirement registry
- Phase 142 backtest window integrity check
- Phase 143 replay leakage guard

Boundary:
- replay validity preflight is research-only
- no edge validation
- no operational edge validation
- no trading signal
- no allocation
- no decision
- no canonical write
