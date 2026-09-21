# Coin Metrics on-chain standalone — conclusion

Date: 2026-09-21

## Frozen hypothesis

`H_CM_ADDR_01`: LONG Bitcoin iff `AdrActCnt_t > AdrActCnt_{t-7}`, with the preregistered full one-day embargo so the state computed on day `t` applies only to `PriceUSD_{t+1} -> PriceUSD_{t+2}`. Transaction cost was fixed at 10 bps per state transition. Baseline was buy-and-hold over the same target-return dates with 10 bps entry and exit costs.

No scientific parameter was changed after observing the result.

## Official standalone run

- workflow run: `35662681632`
- head SHA: `1a32e391a0a366430b9493c630b5427642e363b2`
- artifact: `gate-btc-coinmetrics-onchain-standalone`
- artifact id: `10666774037`
- artifact digest: `sha256:ce2b726693388efb3fe59dad0119f5a7ca10013febb5167e70e5f0c7bcbb0055`
- raw Coin Metrics response SHA256: `6357ea56139e129e4d4657d833320af3cec2889161cbb708dcfdeaebbbebaf1c`

The earlier workflow attempt stopped before any Coin Metrics request because `pytest` was absent from the runner. Installing the test dependency was a mechanical CI fix only; the frozen hypothesis, source, dates, metric, lookback, embargo, costs, baseline and pass rule were unchanged.

## Data capability

The minimum data gate passed:

- valid source rows: `2455`
- causal target-return observations: `2446`
- LONG observations: `1204`
- FLAT observations: `1242`
- duplicate timestamps: `0`
- timestamps strictly increasing: `true`
- state transitions: `958`

Therefore the source demonstrated a tangible historical research capability for this metric and period.

## Economic comparison

### Frozen active-address gate

- final equity: `61958.6970`
- total return: `519.58697%`
- annualized return: `31.28045%`
- annualized volatility: `40.78845%`
- Sharpe-like ratio: `0.76689`
- max drawdown: `-53.12290%`

### Buy-and-hold baseline

- final equity: `103660.0038`
- total return: `936.60004%`
- annualized return: `41.75970%`
- annualized volatility: `59.40620%`
- Sharpe-like ratio: `0.70295`
- max drawdown: `-76.66882%`

### Frozen pass-rule deltas

- drawdown improvement: `+23.54591 percentage points`
- strategy / baseline final-equity ratio: `0.5977107`

The preregistered pass rule required BOTH:

1. drawdown improvement >= `5 pp`; and
2. final equity >= `90%` of baseline.

Condition 1 passed strongly. Condition 2 failed strongly. Therefore:

`feature_pass = false`

## Scientific disposition

`FEATURE_REJECTED / SOURCE_RETAINED_AS_RESEARCH_COMPONENT`

The frozen 7-day positive active-address gate materially reduced drawdown but sacrificed too much terminal equity under the preregistered economics. The 958 transitions are descriptive evidence of how active the rule was, but they do **not** authorize post-outcome smoothing, a different lookback, a threshold change, lower transaction costs, another on-chain metric, or any other rescue retune under `H_CM_ADDR_01`.

Coin Metrics Community API itself remains useful as an external on-chain research data component because the historical capture and causal replay were technically established.

## PIT / integration boundary

This run does not prove the historical response was revision-versioned point-in-time data. Accordingly, historical PIT credit remains zero regardless of the backtest result.

No Factory or BTSE strategy migration is authorized from this run:

- `historical_response_is_revision_versioned_pit_proven=false`
- `prospective_pit_validation_required=true`
- `ECONOMIC_CLAIM_AUTHORIZED=false`
- `FACTORY_MIGRATION_AUTHORIZED=false`

## Safety

- `RESEARCH_ONLY=true`
- `SHADOW_ONLY=true`
- `REAL_CAPITAL_BRL=0`
- `ORDERS=0`
- `NO_RETUNE=true`
- `NO_BACKFILL=true`
- `FACTORY_RUNTIME_UNTOUCHED=true`
