# QRDS Phase 142 - Backtest Window Integrity Check Research-Only

Gate: PHASE142_BACKTEST_WINDOW_INTEGRITY_CHECK_RESEARCH_ONLY_READY_RESEARCH_ONLY

Adds a research-only integrity check for replay/backtest windows.

Checks:
- chronological order
- declared train/test boundary
- no train/test overlap
- positive train duration
- positive test duration

Boundary:
- window integrity is research-only
- valid for decision: False
- no edge validation
- no trading signal
- no allocation
- no decision
- no canonical write
