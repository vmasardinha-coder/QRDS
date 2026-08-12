# GATE BTC — COIN11 Leveraged Capitulation Study v1

Status: RESEARCH_ONLY / SHADOW_ONLY / CREDIT_NOT_AUTHORIZED / ORDERS=0 / CAPITAL_REAL=0
Date frozen: 2026-08-12

## Objective
Test whether financed exposure to COIN11 entered only after Bitcoin capitulation can produce an acceptable risk-adjusted outcome versus BITH11, BTC and no-credit alternatives.

## Entry-region research grid
BTC/USD: 55k, 50k, 47.5k, 45k, 42.5k, 40k, 35k. These are scenario nodes, not authorization levels.

## Reference credit
Net proceeds BRL 294700; 12-month bullet obligation BRL 366654.09; nominal hurdle ~24.4%. Credit parameters must remain replaceable.

## Required data
COIN11 full available history: OHLC, financial/share volume, bid/ask where available, NAV/AUM, holders where available, all distributions, ex/base dates, total return, drawdown. BTC/USD, BTC/BRL, USD/BRL, BITH11 and NEOS BTCI proxy. Volatility realized and implied where sourceable.

## Models
1. Empirical nonlinear BTC/USD + USD/BRL -> COIN11 conditional distribution.
2. Distribution model conditional on COIN11 price, BTC returns/drawdown, realized/implied volatility, trend/lateral regime and option premium proxy.
3. Monte Carlo: historical bootstrap, regime-switching, drawdown-conditioned, stochastic/variable volatility and post-capitulation cycle scenarios. Minimum 10k, validation 50k.
4. Credit engine: 12m bullet; 6m grace then 12/18/24/36 amortization; 24/36/48/60m; investment-backed credit with allowed prepayment.
5. Distribution policies: 100% cash/RF; 100% reinvest; 50/50; debt amortization.
6. Execution engine: ADV, median volume, spread/book where available, slippage for 50k/100k/150k/294.7k and 5/10-slice/VWAP/passive execution.

## Mandatory metrics
Debt coverage probability; external-capital probability; forced-liquidation probability; mean/median and P10/P25/P50/P75/P90 terminal P&L; VaR/CVaR; max drawdown; P(loss >50k/100k/150k); P(profit >50k/100k/200k); return on own capital at risk.

## Stress scenarios
45k->30k; 40k-60k lateral 18m; 45k->90k 12m; 45k->120k; rapid BTC rally / covered-call upside drag; IV collapse; distribution 1.0%/0.5% monthly; USD/BRL -15%; temporary COIN11 liquidity drought; timing-cliff scenario 45k->65k->38k near debt maturity then 90k.

## Governance gate
No recommendation from positive expected value alone. GO requires acceptable ruin/CVaR, external repayment capacity, sufficient liquidity, no forced sale dependency, and statistically material edge over debt cost and no-credit alternative.

Candidate gate to be discovered empirically: BTC<=X AND COIN11<=Y AND current/expected yield>=Z AND liquidity>=L AND CET<=C AND debt-coverage probability>=P.

## Benchmark roles
COIN11 = target income-overlay vehicle. BITH11 = Brazilian spot-BTC control. BTC = pure benchmark. BTCI/NEOS = proxy extension only when COIN11 history is insufficient; proxy results must never be presented as COIN11 observations.

## Current authorization
Study only. Do not contract credit. Do not trade. Do not promote any gate before evidence package is complete.