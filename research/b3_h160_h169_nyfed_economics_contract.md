# B3 H160-H169 — frozen economics implementation contract

Issue: #244

Status: IMPLEMENTATION_FROZEN_BEFORE_FIRST_ECONOMIC_RESULT

This file resolves implementation details left implicit by the H160-H169 preregistration. It is frozen before the first H160-H169 economics run. No result may be used to alter these choices.

## Source and causal admission

Use only the already-admitted Federal Reserve Bank of New York Markets Data API series SOFR, BGCR, TGCR, EFFR and OBFR. Rate and volume views are joined by exact `effectiveDate`. For a B3 signal session `D`, first identify the immediately preceding completed B3 response session `P`; the feature row is the latest official NY Fed `effectiveDate` strictly earlier than `P`. This deliberately adds the preregistered completed-B3-session lag. There is no interpolation, synthetic reconstruction, same-session publication use or proxy substitution.

Before economics, every family must have >=90% finite causal feature coverage separately in discovery (`2024_26`, M5) and replication (`2020_22 + 2022_24`, M15). A coverage failure is DATA_GAP / fail-closed and no economics result is produced.

## Exact standardization frozen before results

For H160/H161/H162 level spreads, `trailing-60 robust standardization` means: current level minus the median of the previous 60 official observations, divided by the unscaled median absolute deviation of those same previous 60 observations around their own median. Exactly 60 prior finite observations are required; zero/non-finite scale yields no signal. No 1.4826 multiplier is applied.

For H163/H164 volume changes, H165/H166 distribution-width changes and H167 log volume-ratio changes, `trailing-20 standardized` means current prescribed change divided by the median absolute value of the previous 20 prescribed changes. Exactly 20 prior finite changes are required; zero/non-finite scale yields no signal.

## Frozen mappings

Positive standardized funding stress maps to WDO long and WIN short; negative stress reverses the signs. Every mapping is paired with its exact inverse. This implements the preregistered `WDO same / WIN risk-off` and `stress/inverse` language consistently without using economic results.

H168 uses only H160/H161/H162 votes at `abs(z)>=1.0`; 2/3 and 3/3 aligned cells are emitted, paired with exact inverses.

H169 is fitted separately for WIN and WDO. For each current signal session, the target is the immediately prior completed response session. Predictors are the causally lagged H160/H161/H162 spread states and H163/H164 volume shocks available to that target session. Rolling windows are exactly 60 and 120 prior finite target observations, OLS with intercept, no regularization. The target residual is divided by the population standard deviation of in-window fitted residuals. Current-session execution decision occurs only after the first 30 minutes; continuation uses the sign of the current first-30m move and mean-reversion uses its exact inverse. Residual thresholds remain 1.5/2.0 and holds remain 60/120m.

## Frozen evaluation and survivor rule

Discovery is `2024_26` M5. Independent replication is pooled `2020_22 + 2022_24` M15. Existing frozen B3 transaction costs, next-bar execution, one-extra-bar delay and hard metric gates are inherited without modification through the canonical B3 metric function. A family survives a sample only if at least one traded leg has >=2 qualified cells with parameter or horizon breadth. Independent replication is mandatory. Maximum two survivors; if more than two replicate, select the lowest frozen family IDs only, never an economics-based ranking.

## Immutable safety

H1 economics unread. Survivor partial prospective economics unread. RESEARCH_ONLY=true. SHADOW_ONLY=true. NOT_APPROVED=true. ORDERS=0. REAL_CAPITAL=0. ENGINE_FEED=false. NO_RETUNE. NO_SYNTHETIC_BACKFILL.
