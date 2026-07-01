# QRDS/QOS • Gate BTC • Risk Model Gate v1

Sprint **8U** adds a research-only risk model gate to the evidence stack.

This gate answers one narrow question:

> Is the risk model documented enough for research review?

It does **not** answer:

- buy;
- sell;
- allocate;
- position size;
- place orders;
- use real capital;
- connect to an authenticated exchange;
- leave `INTERACTIVE_RESEARCH_ONLY` mode.

## Inputs

The CLI may receive upstream evidence artifacts from 8L through 8R:

- Evidence Quality;
- Evidence Drilldown;
- Evidence Timeline;
- Research Promotion;
- Human Review / Policy Lock;
- Out-of-Sample Validation;
- Paper Trading.

The gate may also receive explicit research-only risk fields:

- max portfolio drawdown percentage;
- max symbol exposure percentage;
- daily loss limit percentage;
- stress loss limit percentage;
- kill-switch design presence;
- liquidity constraint presence;
- cost/slippage model presence;
- formal risk artifact presence;
- review state.

## Outputs

The module writes:

- `risk_model_gate.json`;
- `risk_model_gate.md`;
- `risk_model_index.json`;
- `index.html`.

## Usage

From the repo root:

```bash
bash qrds_risk_model_serve.sh \
  --output-dir artifacts/risk_model \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

With prior reports and explicit research-only risk settings:

```bash
bash qrds_risk_model_serve.sh \
  --output-dir artifacts/risk_model \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT \
  --reports crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json,crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json,crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json,crypto_decision_lab/artifacts/research_promotion/research_promotion_gate.json,crypto_decision_lab/artifacts/human_review/human_review_gate.json,crypto_decision_lab/artifacts/oos_validation/oos_validation_gate.json,crypto_decision_lab/artifacts/paper_trading/paper_trading_gate.json \
  --max-portfolio-drawdown-pct 20 \
  --max-symbol-exposure-pct 35 \
  --daily-loss-limit-pct 5 \
  --stress-loss-limit-pct 30 \
  --kill-switch-present \
  --liquidity-check-present \
  --cost-model-present \
  --risk-artifact-present \
  --risk-state UNDER_REVIEW
```

Then open the Codespaces port printed by the serve wrapper.

## Safety contract

The following flags must remain false:

- `operational_decision_allowed`;
- `orders_generated`;
- `real_capital_used`;
- `trading_signal_generated`;
- `executable_signal_generated`;
- `recommendation_generated`;
- `allocation_generated`;
- `portfolio_decision_generated`.

The policy lock remains active even if every research risk criterion is recorded.
