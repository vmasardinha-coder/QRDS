# Gate BTC 2.0 — EURJPY / Repo Stress Hypothesis Extension

Status: **RESEARCH_ONLY / HYPOTHESIS + DATA-READINESS**  
Engine weight: **0**  
Prospective eligibility: **NOT_ELIGIBLE**  
Operational promotion: **PROHIBITED until explicit validation and approval**  
Registered: 2026-09-08

This document extends `GATE_BTC_2_HYPOTHESIS_REGISTRY.md`. It does not replace the canonical registry and does not modify any existing engine weight, strategy rule, threshold, stop, selection rule or operational behavior.

## Family H-EURJPY-REPO — Euro/Yen Stress -> US Repo/Liquidity Transmission

### H-EURJPY-01 — EURJPY as a leading stress composite
A material decline in EURJPY may act as a composite market signal of simultaneous euro-area stress and yen appreciation/repatriation pressure, potentially leading changes in US dollar funding conditions.

EURJPY is a candidate market proxy, not a sufficient causal variable.

### H-EURJPY-02 — French sovereign/bank stress channel
Widening France-vs-Germany sovereign spreads, deterioration in French bank equity/credit proxies and worsening France TARGET2 position may identify a regime in which French financial intermediaries face higher funding pressure.

Candidate observables:
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
- French-bank repo exposure/share from OFR or another auditable primary source.

The source essay claims BNP Paribas, Crédit Agricole and Société Générale collectively account for roughly 20% of repo lending. **This number is not admitted as project fact until reproduced from an OFR-downloadable dataset or another primary auditable source.**

### H-EURJPY-04 — Repo stress -> RMP/SRP response
A sustained rise in repo rates/funding volatility relative to administered rates may increase the probability or scale of Federal Reserve market-function/reserve-management responses, including RMP adjustments and/or Standing Repo usage.

Tests must distinguish:
1. endogenous repo stress;
2. SRP backstop usage;
3. RMP changes aimed at ample reserves;
4. reinvestment purchases;
5. true monetary-policy easing.

### H-EURJPY-05 — EURJPY -> repo stress -> liquidity -> BTC chain
Strong-form source chain:

`EURJPY decline -> France/euro-area financial stress -> reduced repo intermediation -> higher repo funding pressure -> Fed liquidity/reserve-management response -> improved dollar liquidity -> positive BTC response`

Every intermediate link must be validated separately before the composite path is evaluated. A correlation between EURJPY and BTC is insufficient.

### H-EURJPY-06 — Source scenario markers are not thresholds
The source proposes EURJPY moving from roughly 185 toward 140 or below by mid-2027. The project stores 185, 140 and the time target only as **source scenario markers**. They must not be tuned or promoted as engine thresholds without independent validation.

### H-EURJPY-07 — FIMA expansion scenario
Expansion of FIMA repo capacity, limits, tenor or eligible usage could reduce the need for foreign official holders to sell Treasuries during dollar-liquidity stress and could alter global dollar liquidity.

Any removal/increase of current counterparty limits is a **policy scenario**, not a present fact unless confirmed point-in-time from Federal Reserve/New York Fed primary documentation.

### H-EURJPY-08 — ECB/TPI / national-policy alternatives
Euro-area sovereign stress may resolve through ECB/TPI intervention, national fiscal/financial measures, political resolution or market adjustment. The source's unilateral Banque de France QE / "Schrödinger's Euro" scenario is a speculative branch, not the project base case.

## Related H-LIQ extension — RMP impulse

### H-LIQ-06 — Reserve Management Purchase impulse
Changes in the New York Fed's Reserve Management Purchase pace may alter short-term reserve supply, private T-bill availability and repo-market conditions, which may in turn affect BTC through dollar-liquidity and funding channels.

The RMP series must use official New York Fed schedules/results and must distinguish **RMP** from **reinvestment purchases**. RMP is not to be labeled QE by default; official Fed materials frame it as maintaining ample reserves and rate control rather than a change in the monetary-policy stance.

## Primary-source audit snapshot — 2026-09-08

1. **Current RMP caution.** New York Fed operational details show approximately **$0 reserve management purchases** planned for 2026-08-14 through 2026-09-14, alongside approximately $17.0B of reinvestment purchases. Therefore the source claim that the Fed is currently monetizing a fixed percentage of T-bill issuance is not admitted without independent reconstruction.
2. **RMP semantics.** Official Fed/New York Fed material distinguishes RMP from large-scale asset purchases/QE and states that RMPs are used to maintain ample reserves / interest-rate control.
3. **FIMA limits.** Official descriptions use a per-counterparty framework. Any removal/increase is retained only as a future scenario until officially enacted.
4. **French repo share.** The claimed ~20% combined share for BNP Paribas, Crédit Agricole and Société Générale must be reproduced directly from OFR Money Market Fund Monitor downloadable data before use.
5. **Source-date anomaly.** The essay says an average monthly balance-sheet increase occurred "since December 2026" although ingestion is 2026-09-08. This is internally impossible as written and is preserved as a source anomaly; the project must not silently reinterpret it as December 2025.
6. **Political/geopolitical intent.** Claims about the motives of Bessent, the ECB, France, Japan or other governments are not modeled as facts unless evidenced by primary documents.

## Validation contract

Before any prospective eligibility:
- point-in-time data provenance and release-time handling;
- deterministic transforms and runner;
- lead/lag separation from contemporaneous correlation;
- intermediate-link tests for the full transmission chain;
- subperiod and regime stability;
- out-of-sample/prospective validation;
- multiple-hypothesis controls;
- no retrospective threshold tuning without disclosure/versioning;
- separate explicit promotion decision.

## Source ledger entry

`SRC-2026-09-08-HAYES-EURJPY-REPO`

Arthur Hayes / Crypto Trader Digest, essay ingested 2026-09-08. Source thesis: EURJPY as a macro "North Star" for a France/euro-area stress -> French-bank repo contraction -> Fed RMP/FIMA liquidity -> BTC transmission mechanism.

Admitted only as hypotheses and candidate observables. Source political narrative, numerical claims not independently reproduced, EURJPY 140 target, unilateral Banque de France QE scenario and unlimited FIMA usage are **not project facts**.

## Immutable boundary

`RESEARCH_ONLY=True`; engine weight remains zero; no orders, no real capital, no operational activation, and no automatic promotion from source ingestion.
