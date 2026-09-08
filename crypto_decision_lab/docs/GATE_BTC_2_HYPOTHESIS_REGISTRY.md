# Gate BTC 2.0 — Hypothesis Registry

Status: **RESEARCH_ONLY / HYPOTHESIS + DATA-READINESS**  
Engine eligibility: **NOT APPROVED**  
Operational promotion: **PROHIBITED until explicit validation and approval**  
Registered: 2026-08-25  
Last extended: 2026-09-08

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

### H-LIQ-06 — Reserve Management Purchase impulse
Changes in the New York Fed's Reserve Management Purchase (RMP) pace may alter short-term reserve supply, private T-bill availability and repo-market conditions, which may in turn affect BTC through dollar-liquidity and funding channels.

The RMP series must be modeled from official New York Fed operation schedules/results, distinguishing **reserve management purchases** from **reinvestment purchases**. RMPs are not to be labeled QE by default; the Fed explicitly states that their purpose is reserve management / interest-rate control rather than a change in monetary-policy stance.

### Candidate observables
- US 10Y Treasury yield;
- MOVE Index;
- Treasury General Account (TGA);
- Overnight Reverse Repo Facility (ON RRP / RRP);
- banking reserves / reserve balances;
- relevant Fed balance-sheet components;
- Treasury bill share / issuance composition;
- Treasury buybacks by tenor and notional;
- RMP monthly planned amount and actual purchases;
- reinvestment purchases separately from RMP;
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

## Family H-EURJPY-REPO — Euro/Yen Stress -> US Repo/Liquidity Transmission

Classification: **new macro transmission research family**. This family extends H-LIQ; it does not replace it.

### H-EURJPY-01 — EURJPY as a leading stress composite
A material decline in EURJPY may act as a composite market signal of simultaneous euro-area stress and yen appreciation/repatriation pressure, potentially leading changes in US dollar funding conditions.

This is a market-proxy hypothesis. The project does **not** assume EURJPY is causally sufficient by itself.

### H-EURJPY-02 — French sovereign/bank stress channel
Widening France-vs-Germany sovereign spreads, deterioration in French bank equity/credit proxies and worsening France TARGET2 position may identify a regime in which French financial intermediaries face higher funding pressure.

Candidate indicators:
- France 10Y OAT yield;
- Germany 10Y Bund yield;
- OAT-Bund spread;
- BNP Paribas, Crédit Agricole and Société Générale equity relative performance;
- CDS / bank credit spreads where lawful/reliable data are available;
- France TARGET2 balance and change;
- foreign holdings of French sovereign/bank debt where point-in-time data exist.

### H-EURJPY-03 — French-bank repo intermediation contraction
If major French banks reduce Treasury/repo intermediation, US repo rates and funding volatility may rise relative to administered-rate benchmarks.

Required observables:
- SOFR;
- TGCR/BGCR where available;
- IORB;
- SOFR-IORB / TGCR-IORB spreads;
- repo volumes and dealer/MMF counterparty data;
- Standing Repo Facility usage;
- French-bank repo exposure/share from OFR or other auditable sources.

The source essay claims BNP Paribas, Crédit Agricole and Société Générale collectively account for roughly 20% of repo lending. **This number is not admitted as project fact until reproduced from an OFR-downloadable dataset or another primary auditable source.**

### H-EURJPY-04 — Repo stress -> RMP/SRP response
A sustained rise in repo rates/funding volatility relative to administered rates may increase the probability or scale of Federal Reserve market-function/reserve-management responses, including RMP adjustments and/or Standing Repo usage.

This hypothesis must distinguish:
1. endogenous repo stress;
2. SRP backstop usage;
3. RMP changes aimed at ample reserves;
4. reinvestment purchases;
5. true monetary-policy easing.

### H-EURJPY-05 — EURJPY -> repo stress -> liquidity -> BTC chain
The full source narrative can be expressed as a falsifiable transmission chain:

`EURJPY decline -> France/euro-area financial stress -> reduced repo intermediation -> higher repo funding pressure -> Fed liquidity/reserve-management response -> improved dollar liquidity -> positive BTC response`

Validation must test each link separately before testing the composite path. Failure of any intermediate link invalidates the strong-form chain even if EURJPY and BTC happen to correlate.

### H-EURJPY-06 — Threshold/path dependence
The source proposes a directional scenario in which EURJPY falls materially from around 185 toward 140 or below by mid-2027. The project will not encode 185, 140, or a June-2027 deadline as validated thresholds. They may be stored only as **source scenario markers** and evaluated retrospectively/prospectively without tuning.

### H-EURJPY-07 — FIMA expansion scenario
Expansion of FIMA repo capacity, limits, tenor or eligible usage could reduce the need for foreign official holders to sell Treasuries during dollar-liquidity stress and could alter global dollar liquidity.

The current standing facility historically used a per-counterparty limit; any future removal/increase is a **policy scenario**, not a present fact unless confirmed by official Federal Reserve/New York Fed documentation at the point in time tested.

### H-EURJPY-08 — ECB/TPI / national-policy branch
Euro-area sovereign stress may resolve through multiple policy paths, including ECB/TPI intervention, national fiscal/financial measures, political resolution or market adjustment. The source's "Schrödinger's Euro" / unilateral Banque de France QE scenario is treated as a speculative branch, not the base case.

The model must therefore test policy-path alternatives and avoid hard-wiring a single political narrative.

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

## Source-quality / factual-audit notes

External essays are hypothesis generators, not primary data sources. The following 2026-09-08 audit notes apply to the newest EURJPY/repo source:

1. **RMP current-state caution.** Official New York Fed operational details show approximately **$0 reserve management purchases** planned for 2026-08-14 through 2026-09-14, with approximately $17.0B of reinvestment purchases. Therefore a source claim that the Fed is currently monetizing a fixed percentage of bill issuance is not admitted without independent reconstruction.
2. **RMP semantics.** Official Fed/New York Fed material states that RMPs maintain ample reserves and support rate control; they are not, by official classification, a change in monetary-policy stance or the same program as large-scale asset purchases/QE.
3. **FIMA cap.** Historical/current official descriptions use a per-counterparty limit. The essay's removal-of-cap concept is retained only as a future policy scenario unless an official rule change is captured point-in-time.
4. **French repo share.** The claimed ~20% combined share for BNP Paribas, Crédit Agricole and Société Générale requires direct reproduction from OFR Money Market Fund Monitor downloadable data before use.
5. **Source date anomaly.** The essay states an "average monthly increase since December 2026" even though the project ingestion date is 2026-09-08. This is internally impossible as written and is preserved as a source anomaly; the project must not silently reinterpret it as December 2025.
6. **Political/geopolitical claims.** Intent claims attributed to Bessent, the ECB, France, Japan or other governments are not modeled as facts unless evidenced by primary documents. Price and balance-sheet variables are preferred over inferred motive.

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
13. For chain hypotheses, validate intermediate links separately before composite scoring.
14. Political narrative may explain a source thesis but cannot substitute for observables.

---

## Source Ledger

### SRC-2026-08-25-HAYES-SAME-SAME-BUT-DIFFERENT
Arthur Hayes, *Same Same But Different*, Crypto Trader Digest, 2026-08-25.

Admitted for testing: Treasury issuance composition and liquidity; RRP/TGA/reserve channels; Treasury buybacks and long-end yields; MOVE/Treasury stress as a possible policy-response condition; BTC as an early indicator of expected dollar liquidity.

**Source stance is not project stance.** Phrases such as "money printing" are decomposed into testable balance-sheet/liquidity mechanisms before model admission.

### SRC-2026-09-08-HAYES-EURJPY-REPO
Arthur Hayes / Crypto Trader Digest, essay ingested 2026-09-08; source text centers on EURJPY as the author's current macro "North Star" and proposes a France/euro-area stress -> French-bank repo contraction -> Fed RMP/FIMA liquidity -> BTC transmission mechanism.

Admitted for testing:
- EURJPY as a possible leading composite stress indicator;
- OAT-Bund spread, France TARGET2 and French-bank market stress;
- French-bank participation in US repo markets;
- SOFR/TGCR vs IORB and repo-volatility transmission;
- RMP/SRP response functions;
- FIMA capacity as a scenario variable;
- full EURJPY -> repo -> liquidity -> BTC path with intermediate-link validation.

Not admitted as fact without primary verification:
- political intent narratives;
- a fixed/current 39% Fed share of T-bill issuance;
- the ~20% French-bank repo-lending share;
- a guaranteed EURJPY path to 140;
- unilateral Banque de France QE / "Schrödinger's Euro" as a base case;
- unlimited FIMA usage unless officially enacted.

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
| H-EURJPY-REPO | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |
| H-BEH | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |
| H-LIQxBEH | REGISTERED_FOR_RESEARCH | DEPENDS_ON_H-LIQ/H-BEH | 0 | NOT_ELIGIBLE |
| H-RWA | REGISTERED_STRUCTURAL_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |

Registration date: **2026-08-25**.  
Latest source-extension date: **2026-09-08**.
