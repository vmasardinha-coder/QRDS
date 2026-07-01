# QRDS/QOS Evidence Remediation Plan v1

Sprint 8T adds a research-only remediation planner for the 8L → 8R evidence stack.

The planner answers one question:

> Which evidence gaps should be closed next before the stack can even be considered for a later research-gate discussion?

It does **not** answer:

- what to trade;
- whether to allocate;
- how much to size;
- whether to connect an account;
- whether to use real capital;
- whether to generate an executable signal.

## Inputs

The planner can receive prior reports explicitly through `--reports`, or it can auto-discover the standard artifact paths:

- `artifacts/evidence_quality/evidence_quality_gate.json`
- `artifacts/evidence_drilldown/evidence_drilldown_gate.json`
- `artifacts/evidence_timeline/evidence_timeline_gate.json`
- `artifacts/research_promotion/research_promotion_gate.json`
- `artifacts/human_review/human_review_gate.json`
- `artifacts/oos_validation/oos_validation_gate.json`
- `artifacts/paper_trading/paper_trading_gate.json`

## Outputs

- `evidence_remediation_plan.json`
- `evidence_remediation_plan.md`
- `index.html`
- `evidence_remediation_index.json`

## Safety contract

The sprint keeps the QRDS/QOS mode as `INTERACTIVE_RESEARCH_ONLY`.

All operational flags must remain false:

- `orders_generated = false`
- `real_capital_used = false`
- `trading_signal_generated = false`
- `executable_signal_generated = false`
- `recommendation_generated = false`
- `allocation_generated = false`
- `portfolio_decision_generated = false`
- `operational_decision_allowed = false`

## Usage

Generate only:

```bash
cd /workspaces/QRDS
bash qrds_evidence_remediation.sh \
  --output-dir artifacts/evidence_remediation \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Generate and serve:

```bash
cd /workspaces/QRDS
bash qrds_evidence_remediation_serve.sh \
  --output-dir artifacts/evidence_remediation \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Codespaces:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

The terminal can stay attached to the server. Stop it with `Ctrl+C`.
