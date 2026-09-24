# Gate BTC 2.0 — H-AI-CREDIT-LIQ

Status: **RESEARCH_ONLY / HYPOTHESIS + DATA-READINESS**  
Engine weight: **0**  
Prospective eligibility: **NOT_ELIGIBLE**  
Registered: 2026-09-24

## Scope

This family tests whether AI-compute financing stress can propagate through data-center debt, private credit, insurers/reinsurers and commercial-bank balance sheets into dollar liquidity and, ultimately, BTC.

It does **not** assume that an AI-credit problem is bullish for BTC. The path may contain an initial risk-off/deleveraging phase before any policy response.

## H-AI-CREDIT-01 — Compute-demand slowdown

A material slowdown in frontier-model training/inference demand, contracted compute offtake, or AI/data-center capex growth may precede deterioration in AI/data-center credit pricing.

Candidate observables: hyperscaler capex/guidance, disclosed AI-lab commitments, data-center utilization/offtake, power commitments, AI infrastructure issuance, spreads and ratings.

## H-AI-CREDIT-02 — AI/data-center credit stress

Widening spreads, downgrades or impairment in AI/data-center debt may transmit to private-credit vehicles, PE-linked balance sheets and insurers with material exposure.

Required separation: public IG debt, securitized data-center debt, private credit, project finance and equity exposure.

## H-AI-CREDIT-03 — Insurance/reinsurance amplification

Insurer and affiliated-reinsurer structures may amplify credit stress if downgrades or mark-to-market losses increase regulatory capital needs while affiliated reinsurance assets provide insufficient loss-absorbing capacity.

The source claim of a roughly **$1.54T** captive-reinsurance exposure is **UNVERIFIED_SOURCE_CLAIM**. It must not be used quantitatively until reproduced from primary regulatory filings/data.

## H-AI-CREDIT-04 — Commercial-bank liquidity offset

Expansion in commercial-bank assets, loans/securities and deposit money may partially offset contraction or stagnation in Federal Reserve balance-sheet liquidity.

This must be tested jointly with reserves, H.8 bank assets/credit, H.4.1 money/deposits, TGA, ON RRP, RMP/reinvestments and financial-conditions controls. Bank asset growth is not automatically equivalent to QE.

## H-AI-CREDIT-05 — Credit accident first / BTC risk-off

AI/private-credit deterioration may initially tighten financial conditions, widen credit spreads and produce deleveraging/risk-off pressure on BTC before any fiscal or monetary response.

Candidate tests: event studies around downgrades/defaults/spread shocks; BTC 1d/3d/7d/30d forward returns; DXY, MOVE, VIX, credit spreads, repo conditions and crypto leverage controls.

## H-AI-CREDIT-06 — Policy response second / liquidity reversal

If AI/data-center/private-credit/insurance stress becomes systemically material, subsequent fiscal, Fed or regulatory interventions may reverse the liquidity regime and alter BTC's return distribution.

The response must be observed, not presumed. Bailout, guarantee, liquidity facility, regulatory forbearance, government procurement/offtake and conventional monetary easing are distinct mechanisms.

## H-AI-CREDIT-07 — Government compute buyer of last resort

Material US government compute procurement, offtake guarantees or direct AI-infrastructure support could sustain AI/data-center cash flows and capex despite weaker private demand.

Government spending is a fiscal impulse; it must not be labeled `money printing` unless the associated monetary/liquidity mechanism is separately demonstrated.

## H-AI-CREDIT-08 — Cross-family stress interaction

Concurrent AI-credit stress and external funding/repo stress (including H-EURJPY-REPO candidates) may have a different probability, timing and magnitude of policy response than either shock alone.

Required test: joint-state matrix and interaction terms only after both underlying families are independently data-ready.

## Preferred three-block architecture

To limit data mining, do not treat all eight hypotheses as independent trading signals. Organize the family into:

1. **AI / credit stress** — H-AI-CREDIT-01/02/03/05.
2. **Bank / private liquidity** — H-AI-CREDIT-04.
3. **Policy response** — H-AI-CREDIT-06/07, with H-AI-CREDIT-08 as a cross-family interaction.

## Source audit boundary

The Arthur Hayes source is a hypothesis generator, not a primary factual source.

Admitted for testing:
- compute-demand/capex slowdown as a credit trigger;
- AI/data-center debt and private-credit transmission;
- insurer/reinsurer amplification;
- commercial-bank balance-sheet expansion as a possible liquidity offset;
- initial risk-off followed by a possible policy-response/liquidity reversal;
- government compute procurement/offtake as a measurable fiscal scenario.

Not admitted as fact without independent evidence:
- motives attributed to AI labs or public officials;
- inevitability of a US bailout;
- inevitability that either policy path raises BTC;
- broad claims that the US insurance industry is insolvent;
- the approximately $1.54T captive-reinsurance estimate;
- the claim that post-RMP bank balance-sheet growth necessarily made net liquidity stimulative.

## Validation contract

Required progression:

`source -> point-in-time dataset/provenance -> frozen transforms -> intermediate-link tests -> retrospective validation -> robustness/OOS -> prospective eligibility -> explicit promotion decision`

No threshold may be tuned retrospectively without versioning. Each intermediate causal link must be tested separately. Contemporaneous correlation is not sufficient evidence of predictive value.

## Current disposition

| Family | Status | Data-readiness | Engine weight | Prospective eligibility |
|---|---|---|---:|---|
| H-AI-CREDIT-LIQ | REGISTERED_FOR_RESEARCH | TO_BUILD/VERIFY | 0 | NOT_ELIGIBLE |

Flags: `RESEARCH_ONLY=true`, `SHADOW_ONLY=true`, `REAL_CAPITAL=R$0`.
