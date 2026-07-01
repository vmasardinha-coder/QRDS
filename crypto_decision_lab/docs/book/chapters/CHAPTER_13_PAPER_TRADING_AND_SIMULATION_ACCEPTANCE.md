# Chapter 13 - Paper trading and simulation acceptance

        **Status:** CURRENT  
        **Sprint range:** Sprint 8R

        ## Summary

        Documents the paper/simulated observation gate and the difference between simulated fills and real execution.

        ## Key artifacts

        - `docs/reports/PAPER_TRADING_GATE.md`
- `src/crypto_decision_lab/reports/paper_trading.py`

        ## Current limit

        Paper trading is a future acceptance gate, not permission for live-capital deployment.

        ## Next updates

        - Add continuous paper observation window and stability tracking.

        ## Research-only guardrail

        This chapter is documentation only. It does not generate trading signals,
        executable signals, recommendations, allocations, orders, position sizing,
        exchange access, or real-capital instructions.
