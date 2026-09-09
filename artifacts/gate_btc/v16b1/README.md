# GATE BTC V16B.1 — OKX execution family

Status: prospective family version; original V16B remains terminal and is not reopened.

Canonical child: `GATE_BTC_V16B1_OKX_CORE`.
Robustness-only children: `GATE_BTC_V16B1_OKX_COST30_STRESS`, `GATE_BTC_V16B1_OKX_COST50_STRESS`.

Scientific inheritance: V16B signal universe, 18 features, model, score, liquidity floor, portfolio construction, 13-week/20%/1x risk rule, Thursday/Friday clock, 15 bps primary cost, 30/50 bps stress. V16B.1 does not inherit any prospective cycles or risk history from the parent because the short execution venue changed.

Execution change: longs remain Binance Spot USDT. Shorts are exact OKX USDT-settled live SWAP instruments, selected causally from the already-frozen ascending short ranking. Funding and short-price evidence are official OKX only. No third-party substitutions.

First eligible prospective SIGNAL: 2026-09-17. First ENTRY: 2026-09-18. First complete exit/result eligibility: 2026-09-25 after UTC close.

Hard safety: RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED; ENGINE_FEED=false; ORDERS=0; REAL_CAPITAL=0; NO_BACKFILL; NO_LATE_SEAL; NO_RETUNE; FAIL_CLOSED.
