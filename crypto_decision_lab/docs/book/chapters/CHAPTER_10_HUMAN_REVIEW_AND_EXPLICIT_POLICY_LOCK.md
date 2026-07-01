# Chapter 10 - Human review and explicit policy lock

        **Status:** CURRENT  
        **Sprint range:** Sprint 8P

        ## Summary

        Explains the review-state record and why the system cannot self-approve a transition out of research-only mode.

        ## Key artifacts

        - `docs/reports/HUMAN_REVIEW_GATE.md`
- `src/crypto_decision_lab/reports/human_review.py`

        ## Current limit

        Human review recorded inside the tool is not enough to unlock operation; policy change must be explicit and external.

        ## Next updates

        - Add signed review packet concept.

        ## Research-only guardrail

        This chapter is documentation only. It does not generate trading signals,
        executable signals, recommendations, allocations, orders, position sizing,
        exchange access, or real-capital instructions.
