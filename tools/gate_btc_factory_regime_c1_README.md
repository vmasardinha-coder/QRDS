# Factory Regime C1

Issue #166 implementation. This line preserves QOS/defensive incumbents read-only and treats exploratory bottom probabilities only as hypotheses/features, never as truth labels. Five causal regime families are preregistered before results: trend/dispersion, volatility state, rates/FX risk, cross-asset breadth and transition/hysteresis.

Signals are formed only from completed information and applied to next-bar returns. Discovery and replication blocks are separated, fixed switching costs are charged, and survival requires central discovery, neighboring discovery robustness and central independent replication. The rates/FX family fails closed to DATA_GAP if the public FRED series cannot be reproduced.

Any replicated survivor is only ready for freeze. Its prospective D0 must be strictly after freeze/source binding, with no backfill. Comparison capital is R$180,000 only in the normalized reporting layer.
