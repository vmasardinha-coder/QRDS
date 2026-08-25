# Gate BTC 2.0 — Hypothesis Registry

Status: **RESEARCH_ONLY / HYPOTHESIS + DATA-READINESS**  
Engine eligibility: **NOT APPROVED**  
Operational promotion: **PROHIBITED until explicit validation and approval**  
Registered: 2026-08-25

## Purpose

This registry converts external research narratives and recurring project discussions into explicit, falsifiable Gate BTC 2.0 research hypotheses. Registration here does **not** mean a hypothesis is true, predictive, economically useful, calibrated, or eligible for engine weight.

Required progression:

`source idea -> formal hypothesis -> data readiness -> provenance/schema seal -> leakage guards -> deterministic runner -> retrospective validation -> robustness/OOS validation -> prospective eligibility -> explicit promotion decision`

No hypothesis in this document may bypass that progression.

---

## Family H-LIQ — Treasury / Dollar Liquidity

### H-LIQ-01 — TGA / reserves impulse
A decline in the US Treasury General Account (TGA) and/or an increase in banking reserves is associated with a subsequent positive BTC return distribution.

Candidate forward horizons: 1d, 3d, 7d, 30d, 90d. Required transforms: level, delta, rolling z-score, rate of change, and acceleration where defensible.

### H-LIQ-02 — Treasury stress -> policy/liquidity response
A US 10-year Treasury yield approaching a stressed zone, especially when accompanied by a sharp increase in the MOVE Index, raises the conditional probability of a Treasury/Fed liquidity or market-function response.

This is a conditional-response hypothesis, not a rule that high yields are intrinsically bullish for BTC.

### H-LIQ-03 — Treasury buybacks and BTC lead/lag
A material increase in Treasury buybacks that improves long-end market functioning and/or eases financial conditions may precede BTC appreciation, with BTC potentially reacting before slower traditional risk proxies.

### H-LIQ-04 — Bills vs. longer-duration issuance mix
Changes in the Treasury issuance mix between bills and longer-duration securities can alter system liquidity and financial conditions even without a conventional Fed rate cut or headline QE program.

Tests must distinguish balance-sheet money creation, collateral/composition effects, RRP/MMF reallocation, reserve effects, and contemporaneous market reactions. Do not treat all mechanisms as economically identical "money printing" in model outputs.

### H-LIQ-05 — BTC as a liquidity "smoke alarm"
BTC may react to the expected change in dollar liquidity before the full change appears in reported balance-sheet aggregates.

Preferred tests include liquidity level, delta liquidity, liquidity acceleration, and BTC lead/lag versus observed liquidity realization.

### Candidate observables
- US 10Y Treasury yield;
- MOVE Index;
- Treasury General Account (TGA);
- Overnight Reverse Repo Facility (ON RRP / RRP);
- banking reserves / reserve balances;
- relevant Fed balance-sheet components;
- Treasury bill share / issuance composition;
- Treasury buybacks by tenor and notional;
- DXY;
- USDJPY;
- financial-conditions controls;
- BTC spot price, returns and realized volatility.

### MOVE reference condition
The Hayes source essay uses **MOVE > 130** as an acute-stress reference. It is **not** an official ICE threshold and must not be hard-coded into an economic engine without independent validation.

For monitoring only, provisional descriptive bands may be displayed as:
- MOVE < 80: relative calm;
- 80–100: attention;
- 100–120: relevant stress;
- >120: strong stress;
- >130: Hayes acute-stress reference;
- >150: severe stress.

These are operational research labels, not official ICE classifications or validated trading thresholds.

---

## Family H-BEH — Speculative / Hypergamblification Regime

### Methodological boundary
The project does **not** infer or diagnose an individual trader's psychology, dopamine state, addiction, or intent. Behavioral narratives are translated only into observable market-microstructure proxies.

### H-BEH-01 — Leverage build-up regime
Simultaneous growth in open interest, leverage proxies and perpetual-futures volume identifies a higher-intensity speculative regime.

### H-BEH-02 — Crowded-long fragility
Persistent positive funding + rising open interest + slowing/weakening price response increases the conditional risk of a leveraged long flush / liquidation cascade.

### H-BEH-03 — Exhaustion after forced deleveraging
Extreme negative funding and/or severe long liquidation accompanied by a price that stops making proportionate new lows may identify a candidate exhaustion/reversal regime. This is probabilistic, not an automatic buy signal.

### H-BEH-04 — Perpetuals vs. spot hypergamblification proxy
A disproportionate increase in perpetual-derivatives activity relative to spot activity may identify a hypergamblification/speculative-intensity regime.

### H-BEH-05 — Liquidation clustering and volatility expansion
Increasing liquidation frequency and/or liquidation notional intensity may precede or coincide with subsequent volatility expansion. Tests must separate predictive from contemporaneous relationships.

### H-BEH-06 — 24/7 leveraged-market volatility clustering
The interaction of continuous 24/7 trading and leveraged perpetual markets may create volatility/liquidation clusters incompletely represented by traditional market-hours indicators.

### Candidate observables
- aggregate and venue-level perpetual open interest;
- funding rates and funding dispersion;
- estimated leverage ratio / leverage proxies;
- perpetual volume;
- spot volume;
- perp/spot volume ratio;
- futures basis;
- long and short liquidations;
- liquidation count and notional;
- realized and implied volatility where available;
- order-book/liquidity proxies where provenance is reliable;
- stablecoin flows as a control, not as a behavioral diagnosis.

---

## Interaction H-LIQxBEH — Liquidity Ignition vs. Late Speculation

### Core hypothesis
A favorable macro-liquidity impulse combined with **low-to-moderate** speculative intensity may offer a different and potentially more favorable BTC return/risk distribution than favorable liquidity combined with **already-extreme** leverage/hypergamblification.

### Candidate state sequence
1. **Liquidity ignition** — macro/dollar-liquidity impulse improves while speculative intensity remains contained.
2. **Speculative expansion** — spot and derivatives participation broaden.
3. **Late-stage leverage** — funding/OI/perp intensity becomes crowded and reflexive.
4. **Liquidation/reset** — forced deleveraging, volatility spike and regime reset.

The sequence is a hypothesis to be tested, not a presumed deterministic cycle.

Required tests: joint-state matrix, conditional BTC forward returns and drawdowns, transition probabilities, lead/lag analysis, subperiod stability, sensitivity to alternative definitions, and OOS/prospective validation before promotion.

---

## Family H-RWA — Tokenized Market Structure

Classification: **structural / long-horizon research**, not immediate BTC timing.

### H-RWA-01 — TradFi/crypto liquidity integration
Growth in tokenized US equities, ETFs and other RWAs may increase liquidity integration between traditional markets and on-chain/crypto rails.

### H-RWA-02 — Stablecoins as cross-asset settlement layer
Expansion of tokenized securities may strengthen stablecoins as a settlement/funding layer across multiple asset classes.

### H-RWA-03 — Cross-market shock transmission
Greater integration between tokenized traditional assets and crypto infrastructure may increase the speed or strength of shock transmission between TradFi and crypto markets.

### H-RWA-04 — Infrastructure concentration risk
Concentration of execution, clearing, custody, tokenization or issuance infrastructure may create counterparty, operational, legal or systemic risk even when the underlying asset is a regulated traditional security.

These hypotheses require separate structural datasets and must not be mixed into short-horizon BTC timing without evidence.

---

## Validation Guardrails

All families above inherit Gate BTC / QRDS research-only boundaries and additionally require:

1. No engine weight before validation.
2. No automatic activation from article/source ingestion.
3. No retrospective threshold tuning without versioning and disclosure.
4. Point-in-time data and provenance wherever release timing matters.
5. Leakage guards for revised macro series, delayed publication and future-known values.
6. Deterministic runners and frozen transforms before performance evaluation.
7. Predictive vs. contemporaneous separation in all lead/lag claims.
8. Subperiod, regime and out-of-sample testing.
9. Multiple-hypothesis / data-mining controls where many features/horizons are searched.
10. Overlapping-horizon/autocorrelation treatment for multi-day forward returns.
11. Costs/slippage when a hypothesis is ever translated into a tradable rule.
12. No economic-engine promotion without a separately recorded prospective-eligibility and promotion decision.

---

## Source Ledger

### SRC-2026-08-25-HAYES-SAME-SAME-BUT-DIFFERENT
Arthur Hayes, *Same Same But Different*, Crypto Trader Digest, 2026-08-25.

Admitted for testing: Treasury issuance composition and liquidity; RRP/TGA/reserve channels; Treasury buybacks and long-end yields; MOVE/Treasury stress as a possible policy-response condition; BTC as an early indicator of expected dollar liquidity.

**Source stance is not project stance.** Phrases such as "money printing" are decomposed into testable balance-sheet/liquidity mechanisms before model admission.

### SRC-2026-05-25-WUBLOCKCHAIN-PERPETUAL-TRAP
WuBlockchain / Ivan WuBlockchain, *Study: From Rational Trading to Speculative Addiction: How Retail Investors Slip into the Perpetual Trap*, 2026-05-25.

Admitted for testing: perpetual-market speculative intensity; behavioral narratives translated to observable leverage and activity proxies; funding/OI/liquidations as crowding and forced-deleveraging variables; 24/7 leveraged-market regime effects.

Psychological/addiction claims are **not** directly modeled as individual-level facts.

### SRC-2026-06-03-WUBLOCKCHAIN-ALPACA-BSTOCKS
WuBlockchain, *Binance Enters the US Stock Market: Deconstructing Alpaca, the Tokenized Securities Infrastructure Behind bStocks*, 2026-06-03.

Admitted for structural testing: tokenized-equity/RWA integration; stablecoin settlement-layer expansion; TradFi/crypto shock transmission; infrastructure concentration and counterparty risk.

---

## MOVE Monitoring Note

Preferred monitoring references:
- **ICE**: official MOVE Index methodology/data reference;
- **TradingView**: practical chart monitoring via `ICE:MOVE`, subject to vendor availability/licensing.

The project must store source provenance and timestamps when MOVE is added to a sealed dataset. Display bands in this registry are descriptive research labels only.

---

## Current disposition

| Family | Status | Data-readiness | Engine weight | Prospective eligibility |
|---|---|---|---:|---|
| H-LIQ | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |
| H-BEH | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |
| H-LIQxBEH | REGISTERED_FOR_RESEARCH | DEPENDS_ON_H-LIQ/H-BEH | 0 | NOT_ELIGIBLE |
| H-RWA | REGISTERED_STRUCTURAL_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |

Registration date: **2026-08-25**.
