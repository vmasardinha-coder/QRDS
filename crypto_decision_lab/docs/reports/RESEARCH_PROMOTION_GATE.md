# QRDS Research Promotion Gate Matrix v1

Sprint 8O adds a formal research-only promotion matrix after the evidence stack:

- 8L Evidence Quality Gate;
- 8M Evidence Drilldown / Data Coverage Gate;
- 8N Evidence Timeline / Gate History Registry.

It answers:

> Can this hypothesis be promoted to the next research gate while remaining research-only?

It evaluates:

- whether the current evidence gates exist;
- whether their research contracts are intact;
- whether source gate answers are PASS/WATCH/FAIL;
- whether each symbol has a complete evidence trail;
- which formal future gates remain blocked.

It does **not** answer:

- whether to buy;
- whether to sell;
- how much to allocate;
- position sizing;
- portfolio action;
- order placement;
- real-capital usage.

Required safety flags remain false:

- `operational_decision_allowed = False`
- `orders_generated = False`
- `real_capital_used = False`
- `trading_signal_generated = False`
- `executable_signal_generated = False`
- `recommendation_generated = False`
- `allocation_generated = False`
- `portfolio_decision_generated = False`

## Usage

From the repository root in Codespaces:

```bash
cd /workspaces/QRDS
bash qrds_research_promotion.sh \
  --output-dir artifacts/research_promotion \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

To serve the dashboard:

```bash
cd /workspaces/QRDS
bash qrds_research_promotion_serve.sh \
  --output-dir artifacts/research_promotion \
  --symbols BTC-USDT,ETH-USDT,SOL-USDT
```

Then open:

```text
Ports -> porta indicada -> Open in Browser / Open Preview
```

To use real local 8L/8M/8N artifacts:

```bash
bash qrds_research_promotion_serve.sh \
  --output-dir artifacts/research_promotion \
  --reports crypto_decision_lab/artifacts/evidence_quality/evidence_quality_gate.json,crypto_decision_lab/artifacts/evidence_drilldown/evidence_drilldown_gate.json,crypto_decision_lab/artifacts/evidence_timeline/evidence_timeline_gate.json
```

## Interpretation

- `PASS`: a current research gate supports continued research only.
- `WATCH`: a current research gate is partial and needs more evidence.
- `FAIL`: a current research gate blocks promotion to later research gates.
- `BLOCKED_NOT_IMPLEMENTED`: a formal future gate is mandatory but not implemented yet.

Even if the current evidence stack becomes green, the project remains blocked from operational use until these gates exist and pass:

1. data quality / reliability gate;
2. out-of-sample validation;
3. paper trading;
4. formal risk model;
5. human approval;
6. explicit policy change away from research-only.
