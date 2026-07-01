# Chapter 05 - Labels, walk-forward splits, and out-of-sample protocol

        **Status:** CURRENT  
        **Sprint range:** Sprints 5-6 and 8Q

        ## Summary

        Defines how labels, splits, OOS review, leakage guards, embargo expectations, and held-out evidence should be recorded.

        ## Key artifacts

        - `docs/reports/OOS_VALIDATION_GATE.md`
- `src/crypto_decision_lab/reports/oos_validation.py`

        ## Current limit

        8Q records OOS readiness; it does not prove a completed OOS campaign by itself.

        ## Next updates

        - Add actual OOS campaign runner and acceptance window.
- Persist OOS metrics across dates.

        ## Research-only guardrail

        This chapter is documentation only. It does not generate trading signals,
        executable signals, recommendations, allocations, orders, position sizing,
        exchange access, or real-capital instructions.
