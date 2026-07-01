# QRDS/QOS Sprint 8R — Paper Trading Gate v1

## Purpose

The Paper Trading Gate records whether the research evidence stack has enough
paper-only observation maturity to support a future research promotion review.

It answers only:

> Has the hypothesis been observed in a sufficiently controlled paper/research
> setting?

It does **not** answer:

- buy;
- sell;
- allocate;
- position sizing;
- submit an order;
- connect to an exchange account;
- use real capital;
- generate an executable signal;
- recommend a portfolio action.

## Safety contract

The gate remains locked to `INTERACTIVE_RESEARCH_ONLY` and must keep these
flags false:

- `operational_decision_allowed`
- `orders_generated`
- `real_capital_used`
- `trading_signal_generated`
- `executable_signal_generated`
- `recommendation_generated`
- `allocation_generated`
- `portfolio_decision_generated`

## Inputs

Optional prior reports:

- Sprint 8L Evidence Quality Gate
- Sprint 8M Evidence Drilldown Gate
- Sprint 8N Evidence Timeline Gate
- Sprint 8O Research Promotion Gate
- Sprint 8P Human Review / Policy Lock Gate
- Sprint 8Q Out-of-Sample Validation Gate

Optional paper-trading observation metadata:

- `--paper-days`
- `--paper-runs`
- `--simulated-fill-rate`
- `--cost-model-present`
- `--paper-artifact-present`
- `--acceptance-state`

## Usage

```bash
cd /workspaces/QRDS
bash qrds_paper_trading.sh \
  --output-dir artifacts/paper_trading \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

With prior reports:

```bash
bash qrds_paper_trading.sh \
  --output-dir artifacts/paper_trading \
  --reports crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json,crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json,crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json,crypto_decision_lab/artifacts/research_promotion/research_promotion_gate.json,crypto_decision_lab/artifacts/human_review/human_review_gate.json,crypto_decision_lab/artifacts/oos_validation/oos_validation_gate.json \
  --paper-days 30 \
  --paper-runs 20 \
  --simulated-fill-rate 0.95 \
  --cost-model-present \
  --paper-artifact-present \
  --acceptance-state UNDER_REVIEW
```

Serve locally in Codespaces:

```bash
bash qrds_paper_trading_serve.sh \
  --output-dir artifacts/paper_trading \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

## Interpretation

Possible answers include:

- `NO_PAPER_TRADING_NO_INPUT_REPORTS_RESEARCH_ONLY`
- `NO_PAPER_TRADING_ACCEPTANCE_INCOMPLETE_RESEARCH_ONLY`
- `PAPER_TRADING_RESEARCH_OBSERVED_OPERATIONAL_USE_LOCKED_RESEARCH_ONLY`

Even the strongest answer remains research-only and cannot unlock execution.
