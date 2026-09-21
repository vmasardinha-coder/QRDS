# FinRL — Scientific Conclusion — 2026-09-21

## Scope

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- Factory untouched.
- No live capital and no production execution.
- Upstream FinRL SHA: `2334a5fe6d30629157f13c3b0319e1637e15e123`.

The tested hypothesis was a lightweight direct policy-gradient portfolio allocator inspired by FinRL's `PortfolioOptimizationEnv`. This was not a claim of reproducing every FinRL implementation detail.

## Frozen protocol

- OKX: BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT
- 1h
- 6,000 common bars
- data: 2026-01-14 14:00 UTC through 2026-09-21 13:00 UTC
- features: 24h return, 168h return, 24h volatility, 168h volatility
- causal decision semantics: features at t use data ending at t-1; target is t to t+1
- scaler fit on train only
- chronological split: 70% train / 30% untouched test
- 4 risky assets + cash weight
- 20 bps turnover cost
- 5 seeds: 11, 29, 47, 71, 101
- hidden layer 16, tanh, softmax weights
- 120 epochs, learning rate 0.01
- no OOS-driven retuning

## Baselines on untouched test

| Model | Return | Max DD | Annualized Sharpe | Turnover |
|---|---:|---:|---:|---:|
| Equal weight | +42.1318% | -8.9911% | +4.0676 | 2.3014 |
| Positive 24h momentum | -18.6703% | -29.8443% | -1.8925 | 270.4877 |

## Policy-gradient results by seed

| Seed | Train return | Test return | Test Max DD | Test Sharpe | Avg cash weight |
|---|---:|---:|---:|---:|---:|
| 11 | +403.3230% | -6.5476% | -13.0013% | -1.8452 | 76.5% |
| 29 | +320.1897% | -2.2175% | -13.5534% | -0.5127 | 70.9% |
| 47 | +414.8882% | +12.9391% | -5.3181% | +3.0617 | 79.4% |
| 71 | +391.1498% | +1.0120% | -9.8791% | +0.3743 | 83.1% |
| 101 | +412.8415% | -8.6825% | -12.7739% | -3.4147 | 78.7% |

Summary:
- median OOS return: **-2.2175%**
- OOS range: **-8.6825% to +12.9391%**
- positive OOS seeds: **2/5**
- median OOS max drawdown: **-12.7739%**
- median OOS Sharpe: **-0.5127**
- beats equal-weight return: **0/5 seeds**
- beats positive-24h-momentum return: **5/5 seeds**

## Interpretation

The frozen policy shows a large training/OOS generalization gap. All seeds produced very large in-sample returns, but the median untouched result was negative, only two of five seeds were positive, and no seed beat equal weight on return. Seed sensitivity is material.

The policies also allocated roughly 71% to 83% to cash on average out of sample, so the failure is not explained simply by excessive risky exposure. The model learned highly profitable in-sample behavior that did not transfer robustly to the future period.

The weak positive comparison against the 24h momentum control is not sufficient for advancement because that baseline itself lost money and generated very high turnover.

## Decision

`policy_gradient_portfolio_allocation = REJECT_FROZEN_CONFIGURATION / NO_ADVANCE`

`FinRL = CONCLUDED / RETAIN_AS_RL_RESEARCH_SANDBOX`

This rejects the tested frozen configuration, not reinforcement learning or FinRL universally. No architecture, feature, epoch, cost or reward retuning should be performed in response to these OOS results. Any revised RL formulation must be preregistered as a new hypothesis and validated on fresh data.

## Runtime evidence

- workflow run: `35606071477`
- job: `106353342597`
- artifact ID: `10641824371`
- artifact SHA256: `542d44080bb40e1a46f17b88da2b068d8db09ccf76f20afea09a764f9e81c6bb`

No Factory migration was performed.
